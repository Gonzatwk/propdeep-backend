"""Jornada automática para el uso en el PC: publica cada partido y liquida sin hacer nada.

Mientras el servidor está encendido, cada `AUTO_EVERY_MINUTES`:
1. Liquida las predicciones y los picks cuyo partido ya ha terminado.
2. Mira los partidos de la jornada en The Odds API (la lista de partidos no gasta créditos) y
   analiza los que empiezan en menos de `AUTO_HOURS_BEFORE` horas y aún no están publicados.
   Cada partido se analiza una sola vez (mercados x regiones créditos).
"""
from __future__ import annotations

import logging
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.orm import Session

from . import board
from .db import pending
from .picks import pending_with_game
from .track_record import settle

log = logging.getLogger("propdeep.auto")

# La jornada americana va de 12:00 UTC a 12:00 UTC (como OddsClient.events_on). Hasta las
# 06:00 UTC siguen los últimos partidos de la noche anterior.
DAY_ROLLOVER = timedelta(hours=6)


def jornada(now: datetime) -> date:
    return (now - DAY_ROLLOVER).date()


def _start(event: dict) -> datetime | None:
    return board._parse_time(event.get("commence_time"))


def due_events(events: list[dict], published: set[str], now: datetime, hours_before: float) -> list[dict]:
    """Partidos sin publicar que empiezan pronto y aún no han empezado."""
    out = []
    for e in events:
        start = _start(e)
        if e.get("id") in published or start is None:
            continue
        if now < start <= now + timedelta(hours=hours_before):
            out.append(e)
    return out


def tick(session: Session, analyzer, odds, bdl, settings, report: Callable, now: datetime | None = None) -> dict:
    """Una vuelta: liquidar y publicar lo que toque. Devuelve qué ha hecho."""
    now = now or datetime.now(timezone.utc)
    done = {"settled": 0, "published": 0, "events": []}
    if pending(session) or pending_with_game(session):
        done["settled"] = len(settle(session, bdl))

    day = jornada(now)
    due = due_events(odds.events_on(day), board.published_events(session, day.isoformat()), now,
                     settings.auto_hours_before)
    if due:
        from .pipeline import scan_day

        log.warning("Jornada automática: analizando %s partido(s) del %s, tarda unos minutos", len(due), day)
    # Partido a partido, por hora de inicio: el primero sale en la web sin esperar al resto.
    for event in sorted(due, key=lambda e: e.get("commence_time") or ""):
        name = f"{event.get('away_team')} @ {event.get('home_team')}"
        results = scan_day(analyzer, odds, day, events=[event], log=log.info)
        published = board.publish_board(session, results, day, settings.free_lines_per_day, report)
        done["published"] += len(published)
        done["events"].append(name)
        log.warning("Jornada automática: %s, %s líneas publicadas", name, len(published))
    return done


def start(make_session, make_deps: Callable, settings) -> threading.Thread:
    """Lanza el bucle en segundo plano. `make_deps` devuelve (analyzer, odds, bdl, report)."""
    stop = threading.Event()

    def loop():
        while not stop.is_set():
            try:
                with make_session() as session:
                    done = tick(session, *make_deps(), settings)
                if done["settled"] or done["published"]:
                    log.warning("Jornada automática: %s líneas publicadas (%s), %s liquidadas",
                                done["published"], ", ".join(done["events"]) or "-", done["settled"])
            except Exception:  # noqa: BLE001 - un fallo (API caída, sin créditos) no para el bucle
                log.exception("Fallo en la jornada automática; se reintenta en la próxima vuelta")
            stop.wait(settings.auto_every_minutes * 60)

    thread = threading.Thread(target=loop, name="propdeep-auto", daemon=True)
    thread.stop = stop  # type: ignore[attr-defined]
    thread.start()
    return thread
