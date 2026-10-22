"""Cuotas a ganador (moneyline) de cada partido, con todas las casas para compararlas.

Se piden de una vez para toda la jornada (1 crédito por región) y se refrescan como mucho
cada `REFRESH`, así que no pesan en el plan de The Odds API.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import JSON, DateTime, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base

REFRESH = timedelta(minutes=60)


class GameOdds(Base):
    __tablename__ = "game_odds"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    game_date: Mapped[str] = mapped_column(String(10), index=True)
    home_team: Mapped[str] = mapped_column(String(60))
    away_team: Mapped[str] = mapped_column(String(60))
    commence_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    books: Mapped[list] = mapped_column(JSON)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def _parse(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def refresh(session: Session, odds, day: date, now: datetime | None = None, force: bool = False) -> int:
    """Guarda las cuotas de la jornada si las que hay tienen más de una hora. Los partidos ya
    empezados conservan la última cuota antes del inicio (no se piden cuotas en directo)."""
    now = now or datetime.now(timezone.utc)
    rows = {r.event_id: r for r in session.scalars(select(GameOdds).where(GameOdds.game_date == day.isoformat()))}
    pending = [r for r in rows.values() if not r.commence_time or _aware(r.commence_time) > now]
    if not force and rows and (not pending or all(now - _aware(r.fetched_at) < REFRESH for r in pending)):
        return 0
    n = 0
    for g in odds.moneylines(day):
        start = _parse(g["commence_time"])
        if not g["books"] or (start and start <= now and g["event_id"] in rows):
            continue
        row = rows.get(g["event_id"]) or GameOdds(event_id=g["event_id"], game_date=day.isoformat())
        row.home_team, row.away_team, row.commence_time = g["home_team"], g["away_team"], start
        row.books, row.fetched_at = g["books"], now
        session.add(row)
        n += 1
    session.commit()
    return n


def best(books: list[dict]) -> dict:
    if not books:
        return {"home": None, "away": None}
    h = max(books, key=lambda b: b["home_odds"])
    a = max(books, key=lambda b: b["away_odds"])
    return {"home": {"bookmaker": h["bookmaker"], "odds": h["home_odds"]},
            "away": {"bookmaker": a["bookmaker"], "odds": a["away_odds"]}}


def public(row: GameOdds | None, full: bool = False) -> dict | None:
    if row is None:
        return None
    out = {"best": best(row.books), "books_count": len(row.books), "fetched_at": _aware(row.fetched_at).isoformat()}
    if full:
        out["books"] = row.books
    return out


def for_events(session: Session, event_ids: list[str]) -> dict[str, GameOdds]:
    if not event_ids:
        return {}
    return {r.event_id: r for r in session.scalars(select(GameOdds).where(GameOdds.event_id.in_(event_ids)))}
