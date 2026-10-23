"""Liquidación de predicciones y rendimiento real del historial."""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from .clients.balldontlie import BalldontlieClient, minutes
from .db import Prediction, pending

log = logging.getLogger("propdeep.track_record")

# Partido sin terminar tantos días después de su fecha (aplazado o perdido): se anula, como hacen
# las casas, que no esperan a que se juegue otro día.
STALE_DAYS = 3
# Predicción que nunca se emparejó con un partido (p. ej. traspasos del 21-oct): se anula pasado
# este tiempo, porque no hay forma de liquidarla.
UNLINKED_DAYS = 2


# Predicciones sin versión: las del 21-oct-2026, con peso 0,5 y sin el bloqueo de 3 partidos.
OLD_VERSION = "sin versión (antes del 24-oct-2026)"


def grade(side: str, line: float, actual: float) -> str:
    if actual == line:
        return "push"
    went_over = actual > line
    return "won" if went_over == (side == "over") else "lost"


def settle(session: Session, bdl: BalldontlieClient, now: datetime | None = None) -> list:
    """Liquida las predicciones y los picks pendientes cuyo partido ya tiene estadísticas finales.

    Un partido que falla (API caída, datos raros) no frena a los demás: se reintenta en la
    siguiente liquidación."""
    from .picks import pending_ml_unlinked, pending_with_game, refresh_parlays

    now = now or _now()
    try:
        _link_moneylines(session, bdl, pending_ml_unlinked(session))
    except Exception:  # noqa: BLE001 - se reintenta en la próxima liquidación
        session.rollback()
        log.exception("No se pudieron emparejar las apuestas a ganador")
    pend = pending(session)
    settled = _void_unlinked(pend, now)
    by_game: dict[int, list] = defaultdict(list)
    for p in [*pend, *pending_with_game(session)]:
        if p.game_id and p.status == "pending":
            by_game[p.game_id].append(p)
    for game_id, preds in by_game.items():
        try:
            results = _grade_game(bdl, game_id, preds, now)
        except Exception:  # noqa: BLE001 - un partido no debe frenar la liquidación del resto
            log.exception("No se pudo liquidar el partido %s; se reintenta en la próxima vuelta", game_id)
            continue
        for p, status, actual in results:
            p.status, p.actual, p.settled_at = status, actual, now
            settled.append(p)
    session.commit()
    return settled + refresh_parlays(session)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _void_unlinked(preds: list[Prediction], now: datetime) -> list[Prediction]:
    """Anula las predicciones que nunca tuvieron partido de Balldontlie y ya pasó su jornada."""
    limit = (now - timedelta(days=UNLINKED_DAYS)).date().isoformat()
    out = []
    for p in preds:
        if p.game_id is None and p.game_date < limit:
            p.status, p.actual, p.settled_at = "void", None, now
            out.append(p)
    return out


def _grade_game(bdl: BalldontlieClient, game_id: int, preds: list, now: datetime) -> list[tuple]:
    """(predicción, estado, resultado) de las que se pueden liquidar ya. No toca nada: si algo
    falla a medias, el partido queda entero para la próxima vuelta."""
    from .picks import ML

    game = bdl.game(game_id)
    status = str(game.get("status", "")).lower()
    if status != "final":
        stale = (now - timedelta(days=STALE_DAYS)).date().isoformat()
        if "postponed" in status or "cancel" in status or all((p.game_date or "9999") < stale for p in preds):
            # Aplazado o sin jugar: las casas anulan la apuesta.
            return [(p, "void", None) for p in preds]
        return []
    out = []
    for p in preds:
        if getattr(p, "stat", None) == ML:
            margin = _margin(p, game)
            out.append((p, "void" if margin is None else grade("over", 0, margin), margin))
    props = [p for p in preds if getattr(p, "stat", None) != ML]
    if not props:
        return out
    rows = bdl.game_stats(game_id)
    if not rows:
        # "Final" pero sin boxscore todavía: se espera. Anularlo sería perder el resultado.
        return out
    by_player = {(r.get("player") or {}).get("id"): r for r in rows}
    for p in props:
        row = by_player.get(p.player_id)
        if row is None or minutes(row.get("min")) == 0:
            # No jugó: la apuesta se anula en las casas, aquí también.
            out.append((p, "void", None))
        else:
            actual = float(row.get(p.stat) or 0)
            out.append((p, grade(p.side, p.line, actual), actual))
    return out


def _nickname(team: str | None) -> str:
    return (team or "").strip().split(" ")[-1].lower()


def _margin(pick, game: dict) -> float | None:
    """Diferencia de puntos del equipo elegido (positiva si ganó)."""
    home, away = game.get("home_team_score"), game.get("visitor_team_score")
    if home is None or away is None:
        return None
    mine = _nickname(pick.player_name)
    if mine == _nickname((game.get("home_team") or {}).get("full_name")):
        return float(home - away)
    if mine == _nickname((game.get("visitor_team") or {}).get("full_name")):
        return float(away - home)
    return None


def _link_moneylines(session: Session, bdl, picks: list) -> None:
    """Busca el partido de Balldontlie de las apuestas a ganador que aún no lo tienen."""
    by_day = defaultdict(list)
    for p in picks:
        by_day[p.game_date].append(p)
    for day, ps in by_day.items():
        try:
            games = bdl.games_on(datetime.fromisoformat(day).date())
        except Exception:  # noqa: BLE001 - se reintenta en la próxima liquidación
            log.exception("No se pudieron traer los partidos del %s para las apuestas a ganador", day)
            continue
        for p in ps:
            home = _nickname(p.home_team)
            for g in games:
                if _nickname((g.get("home_team") or {}).get("full_name")) == home:
                    p.game_id = g["id"]
                    break
    session.commit()


def summary(predictions: list[Prediction]) -> dict:
    """Rendimiento con apuesta fija de 1 unidad. Cuenta solo jugadas (no 'sin ventaja')."""
    def block(preds: list[Prediction]) -> dict:
        graded = [p for p in preds if p.status in ("won", "lost")]
        won = sum(p.status == "won" for p in graded)
        profit = sum((p.odds - 1) if p.status == "won" else -1 for p in graded)
        return {
            "picks": len(preds),
            "settled": len(graded),
            "won": won,
            "lost": len(graded) - won,
            "push_or_void": sum(p.status in ("push", "void") for p in preds),
            "pending": sum(p.status == "pending" for p in preds),
            "hit_rate": round(won / len(graded), 4) if graded else None,
            "profit_units": round(profit, 2),
            "roi": round(profit / len(graded), 4) if graded else None,
            "avg_odds": round(sum(p.odds for p in graded) / len(graded), 3) if graded else None,
        }

    picks = [p for p in predictions if p.side]
    by_conf, by_version = defaultdict(list), defaultdict(list)
    for p in picks:
        by_conf[p.confidence].append(p)
        by_version[p.model_version or OLD_VERSION].append(p)
    return {
        "overall": block(picks),
        "by_confidence": {k: block(v) for k, v in sorted(by_conf.items())},
        # Para medir el modelo, cada versión por separado: mezclarlas no dice nada.
        "by_version": {k: block(v) for k, v in sorted(by_version.items())},
        "no_bet_analyses": sum(1 for p in predictions if not p.side),
    }
