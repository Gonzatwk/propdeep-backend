"""Zona de partidos: la jornada con todas las líneas analizadas y el muro de pago.

Cada línea analizada se publica en el historial (con su hash), así que todo lo que ve
un suscriptor queda registrado. Antes del partido, el veredicto solo lo ven los
suscriptores y las pocas líneas gratis del día; al empezar el partido se abre a todos.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import Prediction, publish
from .model import Analysis


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
    """Elige las líneas gratis: la de más ventaja de cada partido, por orden de hora,
    sin repetir jugador. Si faltan líneas con ventaja, completa con el resto."""
    if quota <= 0:
        return set()
    order = sorted(range(len(candidates)), key=lambda i: (candidates[i][1].get("commence_time") or "", -candidates[i][0].edge))
    chosen: list[int] = []
    for with_edge_only in (True, False):
        for i in order:
            a, meta = candidates[i]
            if len(chosen) >= quota:
                break
            if i in chosen or (with_edge_only and not a.side):
                continue
            taken = [candidates[j] for j in chosen]
            if any(m.get("event_id") == meta.get("event_id") or c.player == a.player for c, m in taken):
                continue
            chosen.append(i)
    return set(chosen)


def publish_board(
    session: Session,
    results: list,
    day: date,
    free_quota: int,
    write_report: Callable[[Analysis], str],
) -> list[Prediction]:
    """Publica en el historial las líneas de la jornada que aún no estén (no se duplican)."""
    existing = session.scalars(select(Prediction).where(Prediction.game_date == day.isoformat())).all()
    seen = {(p.event_id, p.player_name, p.stat, p.line) for p in existing}
    free_left = free_quota - sum(1 for p in existing if p.free)

    fresh: list[tuple[Analysis, dict]] = []
    for analysis, meta, prop in results:
        key = (meta.get("event_id"), analysis.player, analysis.stat, analysis.line)
        if key in seen:
            continue
        seen.add(key)
        fresh.append((analysis, {
            **meta,
            "commence_time": prop.commence_time,
            "home_team": prop.home_team,
            "away_team": prop.away_team,
        }))

    free = _pick_free(fresh, free_left)
    published = []
    for i, (analysis, meta) in enumerate(fresh):
        meta = {**meta, "free": i in free, "commence_time": _parse_time(meta["commence_time"])}
        published.append(
            publish(session, analysis=analysis.to_dict(), report=write_report(analysis), meta=meta, commit=False)
        )
    session.commit()
    return published


def line_summary(p: Prediction, unlocked: bool) -> dict:
    a = p.analysis or {}
    out = {
        "id": p.id,
        "event_id": p.event_id,
        "player": p.player_name,
        "stat": p.stat,
        "line": p.line,
        "over_odds": a.get("over_odds"),
        "under_odds": a.get("under_odds"),
        "bookmaker": p.bookmaker,
        "free": p.free,
        "locked": not unlocked,
    }
    if unlocked:
        out.update(
            side=p.side,
            odds=p.odds,
            confidence=p.confidence,
            edge=p.edge,
            probability=round(p.prob, 4),
            prob_over=a.get("prob_over_final"),
            prob_over_market=a.get("prob_over_market"),
            projection=a.get("projection"),
            status=p.status,
            actual=p.actual,
        )
    return out


def line_detail(p: Prediction) -> dict:
    a = p.analysis or {}
    return {
        **line_summary(p, True),
        "game": game_header(p),
        "report": p.report,
        "reasons": a.get("reasons", []),
        "expected_value": a.get("expected_value"),
        "trends": a.get("trends"),
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
            "with_edge": sum(1 for p in ps if p.side),
            "free_lines": sum(1 for p in ps if p.free),
            "started": started(ps[0]),
        })
    return sorted(out, key=lambda g: g["commence_time"] or "")
