"""Picks de Gonza: "Ejemplo de mis picks con ayuda de la página".

Son sus apuestas, no las del modelo. Las reglas que hacen creíble la sección:
- Se publican antes de que empiece el partido; después ya no se aceptan.
- No se editan ni se borran: solo se liquidan con el resultado. El hash del contenido
  permite comprobar que nadie los ha tocado.
- Salen todos, también los fallados, con la cuota y la casa.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base, Prediction, content_hash
from .track_record import grade

STATS = ("pts", "reb", "ast", "fg3m", "ml")
# Moneyline (a ganador): player_name guarda el equipo, la línea es 0 y `actual` es la
# diferencia de puntos del equipo elegido, así que grade("over", 0, margen) lo liquida.
ML = "ml"


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
    # Selección de una combinada: no cuenta como pick suelto, cuenta su combinada.
    parlay_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    # Paper bet (simulación en euros): no sale en «Mis picks»; el stake va en euros.
    paper: Mapped[bool] = mapped_column(Boolean, default=False)


class Parlay(Base):
    """Combinada: varias selecciones a una sola cuota. Gana si ganan todas; una anulada
    se quita de la cuota, como hacen las casas."""

    __tablename__ = "parlays"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    odds: Mapped[float] = mapped_column(Float)  # la que da la casa (puede llevar boost)
    bookmaker: Mapped[str] = mapped_column(String(60))
    stake: Mapped[float] = mapped_column(Float, default=1.0)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)
    # Cuota final tras quitar las selecciones anuladas.
    settled_odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paper: Mapped[bool] = mapped_column(Boolean, default=False)


MAX_LEGS = 12


class PickError(ValueError):
    pass


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def create(session: Session, data: dict, now: datetime | None = None) -> Pick:
    """Publica un pick. Si viene de una línea de la zona, el partido y el jugador salen de ella."""
    pick = _build(session, data, now or datetime.now(timezone.utc))
    session.add(pick)
    session.commit()
    return pick


def _moneyline(session: Session, data: dict) -> dict:
    """Apuesta a ganador: el partido sale de las cuotas guardadas (`event_id`) y el equipo de `team`."""
    from .moneyline import GameOdds

    team = (data.get("team") or data.get("player_name") or "").strip()
    if data.get("event_id"):
        g = session.get(GameOdds, data["event_id"])
        if g is None:
            raise PickError("No hay cuotas a ganador de ese partido")
        linked = session.scalars(select(Prediction.game_id).where(
            Prediction.event_id == g.event_id, Prediction.game_id.is_not(None)).limit(1)).first()
        data = {**data, "game_date": g.game_date, "commence_time": _aware(g.commence_time),
                "home_team": g.home_team, "away_team": g.away_team, "game_id": linked}
    if team not in (data.get("home_team"), data.get("away_team")):
        raise PickError("Elige uno de los dos equipos del partido")
    return {**data, "player_name": team, "stat": ML, "line": 0.0, "side": "over", "player_id": None}


def _build(session: Session, data: dict, now: datetime) -> Pick:
    if data.get("stat") == ML:
        data = _moneyline(session, data)
    elif data.get("line_id") is not None:
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
    # Las paper bets (solo las ve el autor) se pueden apuntar con el partido empezado.
    if start <= now and not data.get("paper"):
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
        parlay_id=data.get("parlay_id"),
        paper=bool(data.get("paper")),
    )
    return pick


def create_parlay(session: Session, legs: list[dict], bookmaker: str, odds: float | None = None,
                  stake: float = 1.0, note: str | None = None, now: datetime | None = None,
                  paper: bool = False) -> Parlay:
    """Publica una combinada con sus selecciones, todas antes de que empiece su partido."""
    now = now or datetime.now(timezone.utc)
    if not 2 <= len(legs) <= MAX_LEGS:
        raise PickError(f"Una combinada lleva entre 2 y {MAX_LEGS} selecciones")
    bookmaker = (bookmaker or "").strip()
    if not bookmaker:
        raise PickError("Falta la casa")
    built = [_build(session, {**leg, "bookmaker": bookmaker, "stake": stake, "paper": paper}, now) for leg in legs]
    combined = 1.0
    for leg in built:
        combined *= leg.odds
    odds = float(odds) if odds else round(combined, 2)
    if odds <= 1:
        raise PickError("Cuota no válida")
    parlay = Parlay(
        published_at=now, odds=odds, bookmaker=bookmaker, stake=float(stake or 1.0),
        note=(note or "").strip() or None, status="pending", paper=paper,
        content_hash=content_hash({
            "odds": odds, "bookmaker": bookmaker, "stake": float(stake or 1.0), "published_at": now.isoformat(),
            "legs": [leg.content_hash for leg in built],
        }),
    )
    session.add(parlay)
    session.flush()
    for leg in built:
        leg.parlay_id = parlay.id
        session.add(leg)
    session.commit()
    return parlay


def legs_of(session: Session, parlay_id: int) -> list[Pick]:
    return list(session.scalars(select(Pick).where(Pick.parlay_id == parlay_id).order_by(Pick.commence_time, Pick.id)))


def refresh_parlays(session: Session) -> list[Parlay]:
    """Cierra las combinadas cuyas selecciones ya tienen resultado."""
    done = []
    for parlay in session.scalars(select(Parlay).where(Parlay.status == "pending")):
        legs = legs_of(session, parlay.id)
        statuses = [leg.status for leg in legs]
        if "lost" in statuses:
            parlay.status, parlay.settled_odds = "lost", parlay.odds
        elif "pending" in statuses:
            continue
        else:
            # Las anuladas o nulas salen de la cuota (cuota de la casa / su cuota).
            settled = parlay.odds
            for leg in legs:
                if leg.status in ("void", "push"):
                    settled /= leg.odds
            if all(st in ("void", "push") for st in statuses):
                parlay.status, settled = "void", 1.0
            else:
                parlay.status = "won"
            parlay.settled_odds = round(max(settled, 1.0), 3)
        parlay.settled_at = datetime.now(timezone.utc)
        done.append(parlay)
    session.commit()
    return done


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
    if pick.parlay_id is not None:
        refresh_parlays(session)
    return pick


def pending_with_game(session: Session) -> list[Pick]:
    stmt = select(Pick).where(Pick.status == "pending", Pick.game_id.is_not(None),
                              Pick.player_id.is_not(None) | (Pick.stat == ML))
    return list(session.scalars(stmt))


def pending_ml_unlinked(session: Session) -> list[Pick]:
    """Apuestas a ganador sin partido de Balldontlie (el partido no tenía props publicados)."""
    stmt = select(Pick).where(Pick.status == "pending", Pick.stat == ML, Pick.game_id.is_(None))
    return list(session.scalars(stmt))


def all_picks(session: Session) -> list[Pick]:
    """Picks sueltos (las selecciones de combinadas van con su combinada)."""
    stmt = select(Pick).where(Pick.parlay_id.is_(None), Pick.paper.is_not(True)).order_by(Pick.commence_time.desc(), Pick.id.desc())
    return list(session.scalars(stmt))


def all_parlays(session: Session, paper: bool = False) -> list[tuple[Parlay, list[Pick]]]:
    cond = Parlay.paper.is_(True) if paper else Parlay.paper.is_not(True)
    parlays = session.scalars(select(Parlay).where(cond).order_by(Parlay.published_at.desc(), Parlay.id.desc()))
    return [(p, legs_of(session, p.id)) for p in parlays]


def public_parlay(p: Parlay, legs: list[Pick]) -> dict:
    return {
        "id": p.id,
        "published_at": _aware(p.published_at).isoformat(),
        "commence_time": _aware(min(leg.commence_time for leg in legs)).isoformat() if legs else None,
        "odds": p.odds,
        "settled_odds": p.settled_odds,
        "bookmaker": p.bookmaker,
        "stake": p.stake,
        "note": p.note,
        "status": p.status,
        "content_hash": p.content_hash,
        "legs": [public(leg) for leg in legs],
    }


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
        "auto_settle": p.stat == ML or (p.game_id is not None and p.player_id is not None),
        "content_hash": p.content_hash,
    }


def summary(picks: list) -> dict:
    """Resultado en unidades: cada pick (o combinada) arriesga su stake."""
    graded = [p for p in picks if p.status in ("won", "lost")]
    won = [p for p in graded if p.status == "won"]
    staked = sum(p.stake for p in graded)
    final = lambda p: getattr(p, "settled_odds", None) or p.odds  # noqa: E731
    profit = sum(p.stake * (final(p) - 1) for p in won) - sum(p.stake for p in graded if p.status == "lost")
    return {
        "picks": len(picks),
        "won": len(won),
        "lost": len(graded) - len(won),
        "push_or_void": sum(p.status in ("push", "void") for p in picks),
        "pending": sum(p.status == "pending" for p in picks),
        "hit_rate": round(len(won) / len(graded), 4) if graded else None,
        "profit_units": round(profit, 2),
        "roi": round(profit / staked, 4) if staked else None,
        "avg_odds": round(sum(final(p) for p in graded) / len(graded), 3) if graded else None,
    }
