"""Picks de Gonza: "Ejemplo de mis picks con ayuda de la página".

Son sus apuestas, no las del modelo. Las reglas que hacen creíble la sección:
- Se publican antes de que empiece el partido; después ya no se aceptan.
- No se editan ni se borran: solo se liquidan con el resultado. El hash del contenido
  permite comprobar que nadie los ha tocado.
- Salen todos, también los fallados, con la cuota y la casa.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base, Prediction, content_hash
from .track_record import grade

STATS = ("pts", "reb", "ast", "fg3m")


class Pick(Base):
    __tablename__ = "picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    game_date: Mapped[str] = mapped_column(String(10), index=True)
    commence_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    home_team: Mapped[str | None] = mapped_column(String(60), nullable=True)
    away_team: Mapped[str | None] = mapped_column(String(60), nullable=True)
    player_name: Mapped[str] = mapped_column(String(120))
    stat: Mapped[str] = mapped_column(String(10))
    line: Mapped[float] = mapped_column(Float)
    side: Mapped[str] = mapped_column(String(5))  # over | under
    odds: Mapped[float] = mapped_column(Float)
    bookmaker: Mapped[str] = mapped_column(String(60))
    stake: Mapped[float] = mapped_column(Float, default=1.0)  # unidades
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Línea de la zona de partidos de la que sale (si sale de una): sirve para liquidar sola.
    line_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    game_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    # pending | won | lost | push | void
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)
    actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PickError(ValueError):
    pass


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def create(session: Session, data: dict, now: datetime | None = None) -> Pick:
    """Publica un pick. Si viene de una línea de la zona, el partido y el jugador salen de ella."""
    now = now or datetime.now(timezone.utc)
    if data.get("line_id") is not None:
        p = session.get(Prediction, data["line_id"])
        if p is None or not p.event_id:
            raise PickError("Esa línea no está en la zona de partidos")
        data = {
            **data,
            "game_date": p.game_date,
            "commence_time": _aware(p.commence_time),
            "home_team": p.home_team,
            "away_team": p.away_team,
            "player_name": p.player_name,
            "stat": p.stat,
            "line": data.get("line") if data.get("line") is not None else p.line,
            "game_id": p.game_id,
            "player_id": p.player_id,
        }
    start = _aware(data.get("commence_time"))
    if start is None:
        raise PickError("Falta la hora del partido")
    if start <= now:
        raise PickError("El partido ya ha empezado: los picks se publican antes")
    if data.get("stat") not in STATS:
        raise PickError("Estadística no válida")
    if data.get("side") not in ("over", "under"):
        raise PickError("Elige más o menos")
    if not data.get("odds") or data["odds"] <= 1:
        raise PickError("Cuota no válida")
    if not (data.get("player_name") or "").strip() or not (data.get("bookmaker") or "").strip():
        raise PickError("Faltan el jugador o la casa")

    record = {
        "game_date": data.get("game_date") or start.date().isoformat(),
        "commence_time": start.isoformat(),
        "home_team": data.get("home_team"),
        "away_team": data.get("away_team"),
        "player_name": data["player_name"].strip(),
        "stat": data["stat"],
        "line": float(data["line"]),
        "side": data["side"],
        "odds": float(data["odds"]),
        "bookmaker": data["bookmaker"].strip(),
        "stake": float(data.get("stake") or 1.0),
        "note": (data.get("note") or "").strip() or None,
    }
    pick = Pick(
        **{**record, "commence_time": start},
        published_at=now,
        line_id=data.get("line_id"),
        game_id=data.get("game_id"),
        player_id=data.get("player_id"),
        content_hash=content_hash({**record, "published_at": now.isoformat()}),
        status="pending",
    )
    session.add(pick)
    session.commit()
    return pick


def settle_manual(session: Session, pick_id: int, actual: float | None, void: bool = False) -> Pick:
    """Liquida a mano un pick pendiente (para los que no salen de la zona). Solo una vez."""
    pick = session.get(Pick, pick_id)
    if pick is None:
        raise LookupError("Pick no encontrado")
    if pick.status != "pending":
        raise PickError("Este pick ya está liquidado y no se puede cambiar")
    if _aware(pick.commence_time) > datetime.now(timezone.utc):
        raise PickError("El partido aún no ha empezado")
    if void:
        pick.status, pick.actual = "void", None
    elif actual is None:
        raise PickError("Falta el resultado")
    else:
        pick.actual = float(actual)
        pick.status = grade(pick.side, pick.line, pick.actual)
    pick.settled_at = datetime.now(timezone.utc)
    session.commit()
    return pick


def pending_with_game(session: Session) -> list[Pick]:
    stmt = select(Pick).where(Pick.status == "pending", Pick.game_id.is_not(None), Pick.player_id.is_not(None))
    return list(session.scalars(stmt))


def all_picks(session: Session) -> list[Pick]:
    return list(session.scalars(select(Pick).order_by(Pick.commence_time.desc(), Pick.id.desc())))


def public(p: Pick) -> dict:
    return {
        "id": p.id,
        "published_at": _aware(p.published_at).isoformat(),
        "commence_time": _aware(p.commence_time).isoformat(),
        "game_date": p.game_date,
        "home_team": p.home_team,
        "away_team": p.away_team,
        "player": p.player_name,
        "stat": p.stat,
        "line": p.line,
        "side": p.side,
        "odds": p.odds,
        "bookmaker": p.bookmaker,
        "stake": p.stake,
        "note": p.note,
        "status": p.status,
        "actual": p.actual,
        "auto_settle": p.game_id is not None and p.player_id is not None,
        "content_hash": p.content_hash,
    }


def summary(picks: list[Pick]) -> dict:
    """Resultado en unidades: cada pick arriesga su stake."""
    graded = [p for p in picks if p.status in ("won", "lost")]
    won = [p for p in graded if p.status == "won"]
    staked = sum(p.stake for p in graded)
    profit = sum(p.stake * (p.odds - 1) for p in won) - sum(p.stake for p in graded if p.status == "lost")
    return {
        "picks": len(picks),
        "won": len(won),
        "lost": len(graded) - len(won),
        "push_or_void": sum(p.status in ("push", "void") for p in picks),
        "pending": sum(p.status == "pending" for p in picks),
        "hit_rate": round(len(won) / len(graded), 4) if graded else None,
        "profit_units": round(profit, 2),
        "roi": round(profit / staked, 4) if staked else None,
        "avg_odds": round(sum(p.odds for p in graded) / len(graded), 3) if graded else None,
    }
