"""Jornada automática para el uso en el PC: publica cada partido y liquida sin hacer nada.

Mientras el servidor está encendido, cada `AUTO_EVERY_MINUTES`:
1. Liquida las predicciones y los picks cuyo partido ya ha terminado.
2. Mira los partidos de la jornada en The Odds API (la lista de partidos no gasta créditos) y
   analiza los que empiezan en menos de `AUTO_HOURS_BEFORE` horas y aún no están publicados.
   Cada análisis cuesta mercados x regiones créditos. Si un partido sale sin líneas o con algún
   mercado sin colgar, se vuelve a mirar como mucho dos veces más, a 3 h y a 1 h del inicio.
3. Refresca las cuotas a ganador de la jornada como mucho cada hora (1 crédito por región).
"""
from __future__ import annotations

import logging
import threading
from datetime import date, datetime, timedelta, timezone
from typing import Callable

from sqlalchemy.orm import Session

from . import board, moneyline
from .clients.odds import MARKETS
from .db import pending
from .picks import pending_ml_unlinked, pending_with_game
from .track_record import settle

log = logging.getLogger("propdeep.auto")

# La jornada americana va de 12:00 UTC a 12:00 UTC (como OddsClient.events_on). Hasta las
# 06:00 UTC siguen los últimos partidos de la noche anterior.
DAY_ROLLOVER = timedelta(hours=6)


def jornada(now: datetime) -> date:
    return (now - DAY_ROLLOVER).date()


def _start(event: dict) -> datetime | None:
    return board._parse_time(event.get("commence_time"))


# Repasos de un partido incompleto: horas antes del inicio y separación mínima entre peticiones.
RESCAN_HOURS = (3.0, 1.0)
RESCAN_GAP = timedelta(minutes=60)
ALL_STATS = frozenset(MARKETS.values())


def due_events(events: list[dict], published: dict[str, set[str]], scans: dict[str, tuple[int, datetime]],
               now: datetime, hours_before: float) -> list[dict]:
    """Partidos por empezar que toca analizar: los que nunca se miraron, cuando faltan menos de
    `hours_before` horas, y los incompletos (sin líneas o sin algún mercado), en los repasos."""
    out = []
    for e in events:
        start = _start(e)
        if start is None or not now < start <= now + timedelta(hours=hours_before):
            continue
        stats = published.get(e.get("id"), set())
        # Publicado antes de llevar la cuenta (o a mano con /admin/board): cuenta como una vez.
        n, last = scans.get(e.get("id"), (1 if stats else 0, None))
        if n == 0:
            out.append(e)
            continue
        if ALL_STATS <= stats or n > len(RESCAN_HOURS):
            continue
        if start - now <= timedelta(hours=RESCAN_HOURS[n - 1]) and (last is None or now - last >= RESCAN_GAP):
            out.append(e)
    return out


def tick(session: Session, analyzer, odds, bdl, settings, report: Callable, now: datetime | None = None) -> dict:
    """Una vuelta: liquidar y publicar lo que toque. Devuelve qué ha hecho."""
    now = now or datetime.now(timezone.utc)
    done = {"settled": 0, "published": 0, "events": []}
    if pending(session) or pending_with_game(session) or pending_ml_unlinked(session):
        try:
            done["settled"] = len(settle(session, bdl, now))
        except Exception:  # noqa: BLE001 - sin liquidar se sigue publicando
            session.rollback()
            log.exception("No se pudo liquidar; se reintenta en la próxima vuelta")

    day = jornada(now)
    try:
        moneyline.refresh(session, odds, day, now)
    except Exception:  # noqa: BLE001 - sin cuotas a ganador se sigue publicando
        session.rollback()
        log.exception("No se pudieron traer las cuotas a ganador")
    due = due_events(odds.events_on(day), board.published_stats(session, day.isoformat()),
                     board.scans(session, day.isoformat()), now, settings.auto_hours_before)
    if due:
        from .pipeline import scan_day

        log.warning("Jornada automática: analizando %s partido(s) del %s, tarda unos minutos", len(due), day)
    # Partido a partido, por hora de inicio: el primero sale en la web sin esperar al resto.
    for event in sorted(due, key=lambda e: e.get("commence_time") or ""):
        name = f"{event.get('away_team')} @ {event.get('home_team')}"
        published = []
        try:
            results = scan_day(analyzer, odds, day, events=[event], log=log.info)
            published = board.publish_board(session, results, day, settings.free_lines_per_day, report)
        except Exception:  # noqa: BLE001 - un partido que falla no frena al resto
            session.rollback()
            log.exception("Jornada automática: falló %s", name)
        # Se apunta aunque falle: cada petición cuesta créditos y no debe repetirse sin fin.
        board.record_scan(session, event.get("id"), day.isoformat(), now, len(published))
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
                analyzer, odds, bdl, report = make_deps()
                with make_session() as session:
                    done = tick(session, analyzer, odds, bdl, settings, report)
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
