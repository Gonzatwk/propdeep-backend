"""Boxscores de todos los partidos guardados en la base de datos.

Por qué: la defensa del rival por posición, el ritmo y el uso necesitan las estadísticas de TODOS
los jugadores de cada partido, no solo las del jugador analizado. Pedirlas cada vez gastaría el
límite de Balldontlie; se guardan una vez por jornada terminada y se calculan en local.

Solo se guardan los partidos terminados ("Final") y los jugadores con minutos. Repetir la
sincronización no duplica nada (una fila por partido y jugador).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import Boolean, Float, Integer, String, UniqueConstraint, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .clients.balldontlie import minutes
from .db import Base

log = logging.getLogger("propdeep.boxscores")

# Días hacia atrás que se repasan en cada vuelta (partidos que acabaron tarde o se corrigieron).
RECHECK_DAYS = 3


class BoxScore(Base):
    __tablename__ = "box_scores"
    __table_args__ = (UniqueConstraint("game_id", "player_id", name="uq_box_game_player"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(Integer, index=True)
    game_date: Mapped[str] = mapped_column(String(10), index=True)
    season: Mapped[int] = mapped_column(Integer, index=True)
    player_id: Mapped[int] = mapped_column(Integer, index=True)
    player_name: Mapped[str] = mapped_column(String(120))
    position: Mapped[str] = mapped_column(String(8), default="")
    team_id: Mapped[int] = mapped_column(Integer, index=True)
    opponent_id: Mapped[int] = mapped_column(Integer, index=True)
    home: Mapped[bool] = mapped_column(Boolean)
    minutes: Mapped[float] = mapped_column(Float)
    pts: Mapped[float] = mapped_column(Float)
    reb: Mapped[float] = mapped_column(Float)
    ast: Mapped[float] = mapped_column(Float)
    fg3m: Mapped[float] = mapped_column(Float)
    fga: Mapped[float] = mapped_column(Float)
    fta: Mapped[float] = mapped_column(Float)
    oreb: Mapped[float] = mapped_column(Float)
    tov: Mapped[float] = mapped_column(Float)


def to_box(row: dict) -> BoxScore | None:
    """Fila de /stats de Balldontlie -> BoxScore. None si no sirve (sin minutos, sin terminar,
    playoffs o datos incompletos)."""
    game, team, player = row.get("game") or {}, row.get("team") or {}, row.get("player") or {}
    mins = minutes(row.get("min"))
    if mins <= 0 or str(game.get("status", "")).lower() != "final" or game.get("postseason"):
        return None
    home_id, visitor_id, team_id = game.get("home_team_id"), game.get("visitor_team_id"), team.get("id")
    if None in (game.get("id"), player.get("id"), team_id, home_id, visitor_id):
        return None
    home = team_id == home_id
    num = lambda k: float(row.get(k) or 0)  # noqa: E731
    return BoxScore(
        game_id=game["id"], game_date=str(game.get("date", ""))[:10], season=game.get("season") or 0,
        player_id=player["id"], player_name=f"{player.get('first_name', '')} {player.get('last_name', '')}".strip(),
        position=player.get("position") or "", team_id=team_id, opponent_id=visitor_id if home else home_id,
        home=home, minutes=mins, pts=num("pts"), reb=num("reb"), ast=num("ast"), fg3m=num("fg3m"),
        fga=num("fga"), fta=num("fta"), oreb=num("oreb"), tov=num("turnover"),
    )


def store(session: Session, rows: list[dict]) -> int:
    """Guarda las filas que falten. Devuelve cuántas son nuevas."""
    boxes = [b for b in (to_box(r) for r in rows) if b is not None]
    if not boxes:
        return 0
    stmt = select(BoxScore.game_id, BoxScore.player_id).where(BoxScore.game_id.in_({b.game_id for b in boxes}))
    have = {(g, p) for g, p in session.execute(stmt)}
    fresh = [b for b in boxes if (b.game_id, b.player_id) not in have]
    session.add_all(fresh)
    session.commit()
    return len(fresh)


def sync(session: Session, bdl, season: int, today: date, start: date | None = None) -> int:
    """Trae los boxscores de las jornadas terminadas que falten, hasta ayer.

    Sin nada guardado de esa temporada, empieza en `start` (por defecto el 1 de octubre). Después
    solo repasa los últimos RECHECK_DAYS días y lo que falte desde la última jornada guardada."""
    last = session.scalar(select(func.max(BoxScore.game_date)).where(BoxScore.season == season))
    if last:
        day = min(date.fromisoformat(last) + timedelta(days=1), today - timedelta(days=RECHECK_DAYS))
    else:
        day = start or date(season, 10, 1)
    new = 0
    while day < today:
        new += store(session, bdl.stats_on(day))
        day += timedelta(days=1)
    if new:
        log.info("Boxscores: %s filas nuevas hasta el %s", new, today - timedelta(days=1))
    return new


def rows_between(session: Session, season: int, before: str) -> list[BoxScore]:
    """Boxscores de una temporada anteriores a una fecha (nunca información futura)."""
    stmt = select(BoxScore).where(BoxScore.season == season, BoxScore.game_date < before)
    return list(session.scalars(stmt))

