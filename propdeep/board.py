"""Zona de partidos: la jornada con todas las líneas analizadas y el muro de pago.

Modo análisis: se enseñan datos (proyección, % sobre la línea, desgloses, rival y las
líneas de cada casa), nunca un "más/menos" como recomendación. El backtest de 2025-26 no
mostró ventaja frente a las casas, así que el veredicto interno del modelo se guarda para
seguir midiéndolo, pero no sale de la API. Antes del partido, el análisis solo lo ven los
suscriptores y las pocas líneas gratis del día; al empezar el partido se abre a todos.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import DateTime, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from . import fair, feed
from .db import Base, Prediction, publish
from .model import Analysis


class EventScan(Base):
    """Cada vez que se piden las cuotas de un partido (cuesta créditos). Sirve para no volver a
    pedir sin fin un partido sin líneas y para repasar los que salieron a medias."""
    __tablename__ = "event_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), index=True)
    game_date: Mapped[str] = mapped_column(String(10), index=True)
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    lines: Mapped[int] = mapped_column(Integer, default=0)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def started(p: Prediction, now: datetime | None = None) -> bool:
    start = _aware(p.commence_time)
    return start is None or start <= (now or _now())


def is_unlocked(p: Prediction, subscriber: bool, now: datetime | None = None) -> bool:
    return subscriber or p.free or started(p, now)


def _pick_free(candidates: list[tuple[Analysis, dict]], quota: int) -> set[int]:
    """Elige las líneas gratis: una por partido, por orden de hora, sin repetir jugador.
    En cada partido, los puntos del jugador con más proyección (el que más se busca).
    No usa el veredicto del modelo: lo gratis no debe parecer una recomendación."""
    if quota <= 0:
        return set()
    order = sorted(range(len(candidates)), key=lambda i: (
        candidates[i][1].get("commence_time") or "",
        candidates[i][0].stat != "pts",
        -candidates[i][0].projection,
    ))
    chosen: list[int] = []
    for i in order:
        a, meta = candidates[i]
        if len(chosen) >= quota:
            break
        taken = [candidates[j] for j in chosen]
        if any(m.get("event_id") == meta.get("event_id") or c.player == a.player for c, m in taken):
            continue
        chosen.append(i)
    for i in order:  # pocos partidos: completa con el resto
        if len(chosen) >= quota:
            break
        if i not in chosen and all(candidates[j][0].player != candidates[i][0].player for j in chosen):
            chosen.append(i)
    return set(chosen)


def publish_board(
    session: Session,
    results: list,
    day: date,
    free_quota: int,
    write_report: Callable[[Analysis, dict], str],
) -> list[Prediction]:
    """Publica en el historial las líneas de la jornada que aún no estén (no se duplican).
    Una línea por jugador y estadística: si la casa la mueve, se queda la primera publicada."""
    existing = session.scalars(select(Prediction).where(Prediction.game_date == day.isoformat())).all()
    seen = {(p.event_id, p.player_name, p.stat) for p in existing}
    free_left = free_quota - sum(1 for p in existing if p.free)

    fresh: list[tuple[Analysis, dict]] = []
    for analysis, meta, prop in results:
        key = (meta.get("event_id"), analysis.player, analysis.stat)
        if key in seen:
            continue
        seen.add(key)
        fresh.append((analysis, {
            **meta,
            "books": meta.get("books") or [],
            "commence_time": prop.commence_time,
            "home_team": prop.home_team,
            "away_team": prop.away_team,
        }))

    free = _pick_free(fresh, free_left)
    published = []
    for i, (analysis, meta) in enumerate(fresh):
        meta = {**meta, "free": i in free, "commence_time": _parse_time(meta["commence_time"])}
        data = {**analysis.to_dict(), "books": meta["books"],
                # Precio justo y probabilidad estimada (calibrada): base del feed y las combinadas.
                "estimate": fair.estimate(analysis.stat, analysis.line, analysis.prob_over_model,
                                          analysis.prob_over_market, analysis.trends.sd, meta["books"])}
        published.append(
            publish(session, analysis=data, report=write_report(analysis, meta), meta=meta, commit=False)
        )
    session.flush()  # ids para las tarjetas del feed
    feed.publish_cards(session, published)
    session.commit()
    return published


def _hit_rates(t: dict) -> dict:
    return {
        "last5": t.get("hit_rate_last5"),
        "last10": t.get("hit_rate_last10"),
        "season": t.get("hit_rate_season"),
        "season_games": t.get("season_games", 0),
        "last_season": t.get("hit_rate_last_season"),
        "last_season_games": t.get("last_season_games", 0),
    }


def best_prices(books: list[dict]) -> dict:
    """Mejor opción para el más (línea más baja; a igualdad, más cuota) y para el menos."""
    if not books:
        return {"over": None, "under": None}
    over = min(books, key=lambda b: (b["line"], -b["over_odds"]))
    under = max(books, key=lambda b: (b["line"], b["under_odds"]))
    pick = lambda b, k: {"bookmaker": b["bookmaker"], "line": b["line"], "odds": b[k]}  # noqa: E731
    return {"over": pick(over, "over_odds"), "under": pick(under, "under_odds")}


def line_summary(p: Prediction, unlocked: bool) -> dict:
    a = p.analysis or {}
    books = a.get("books") or []
    out = {
        "id": p.id,
        "event_id": p.event_id,
        "player": p.player_name,
        "stat": p.stat,
        "line": p.line,
        "over_odds": a.get("over_odds"),
        "under_odds": a.get("under_odds"),
        "bookmaker": p.bookmaker,
        "books_count": len({b["bookmaker"] for b in books}) or 1,
        "free": p.free,
        "locked": not unlocked,
    }
    if unlocked:
        out.update(
            projection=a.get("projection"),
            hit_rates=_hit_rates(a.get("trends") or {}),
            best=best_prices(books),
        )
    else:
        # Muro con curiosidad: se dice sobre cuántos partidos es el dato, nunca el dato.
        out["teaser_games"] = min(10, (a.get("trends") or {}).get("games") or 0) or None
    return out


def line_detail(p: Prediction) -> dict:
    a = p.analysis or {}
    trends = a.get("trends") or {}
    return {
        **line_summary(p, True),
        "game": game_header(p),
        "report": p.report,
        "notes": a.get("reasons", []),
        "books": a.get("books") or [],
        "trends": {k: v for k, v in trends.items() if not k.startswith("hit_rate")},
        "context": a.get("context"),
        "published_at": _aware(p.published_at).isoformat(),
        "content_hash": p.content_hash,
    }


def game_header(p: Prediction) -> dict:
    start = _aware(p.commence_time)
    return {
        "event_id": p.event_id,
        "game_date": p.game_date,
        "home_team": p.home_team,
        "away_team": p.away_team,
        "commence_time": start.isoformat() if start else None,
    }


def board_lines(session: Session, game_date: str | None = None, event_id: str | None = None) -> list[Prediction]:
    stmt = select(Prediction).where(Prediction.event_id.is_not(None))
    if game_date:
        stmt = stmt.where(Prediction.game_date == game_date)
    if event_id:
        stmt = stmt.where(Prediction.event_id == event_id)
    return list(session.scalars(stmt.order_by(Prediction.commence_time, Prediction.player_name, Prediction.stat)))


def published_events(session: Session, game_date: str) -> set[str]:
    stmt = select(Prediction.event_id).where(Prediction.game_date == game_date, Prediction.event_id.is_not(None))
    return set(session.scalars(stmt.distinct()))


def published_stats(session: Session, game_date: str) -> dict[str, set[str]]:
    """Estadísticas con alguna línea publicada, por partido."""
    stmt = select(Prediction.event_id, Prediction.stat).where(
        Prediction.game_date == game_date, Prediction.event_id.is_not(None)).distinct()
    out: dict[str, set[str]] = defaultdict(set)
    for event_id, stat in session.execute(stmt):
        out[event_id].add(stat)
    return dict(out)


def record_scan(session: Session, event_id: str, game_date: str, when: datetime, lines: int) -> None:
    session.add(EventScan(event_id=event_id, game_date=game_date, scanned_at=when, lines=lines))
    session.commit()


def scans(session: Session, game_date: str) -> dict[str, tuple[int, datetime]]:
    """Por partido: cuántas veces se han pedido sus cuotas y cuándo fue la última."""
    out: dict[str, tuple[int, datetime]] = {}
    for s in session.scalars(select(EventScan).where(EventScan.game_date == game_date)):
        n, last = out.get(s.event_id, (0, None))
        when = _aware(s.scanned_at)
        out[s.event_id] = (n + 1, when if last is None or when > last else last)
    return out


def board_dates(session: Session) -> list[str]:
    stmt = select(Prediction.game_date).where(Prediction.event_id.is_not(None)).distinct()
    return sorted(session.scalars(stmt))


def default_date(session: Session, now: datetime | None = None) -> str | None:
    """La primera jornada con algún partido sin terminar; si no hay, la última."""
    now = now or _now()
    dates = board_dates(session)
    for d in dates:
        lines = board_lines(session, game_date=d)
        if any(_aware(p.commence_time) and _aware(p.commence_time) > now - timedelta(hours=4) for p in lines):
            return d
    return dates[-1] if dates else None


def games(lines: list[Prediction]) -> list[dict]:
    grouped: dict[str, list[Prediction]] = defaultdict(list)
    for p in lines:
        grouped[p.event_id].append(p)
    out = []
    for ps in grouped.values():
        out.append({
            **game_header(ps[0]),
            "lines": len(ps),
            "players": len({p.player_name for p in ps}),
            "free_lines": sum(1 for p in ps if p.free),
            "started": started(ps[0]),
        })
    return sorted(out, key=lambda g: g["commence_time"] or "")
