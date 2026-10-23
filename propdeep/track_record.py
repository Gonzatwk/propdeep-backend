"""Liquidación de predicciones y rendimiento real del historial."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .clients.balldontlie import BalldontlieClient, minutes
from .db import Prediction, pending


# Predicciones sin versión: las del 21-oct-2026, con peso 0,5 y sin el bloqueo de 3 partidos.
OLD_VERSION = "sin versión (antes del 24-oct-2026)"


def grade(side: str, line: float, actual: float) -> str:
    if actual == line:
        return "push"
    went_over = actual > line
    return "won" if went_over == (side == "over") else "lost"


def settle(session: Session, bdl: BalldontlieClient) -> list:
    """Liquida las predicciones y los picks pendientes cuyo partido ya tiene estadísticas finales."""
    from .picks import ML, pending_ml_unlinked, pending_with_game, refresh_parlays

    _link_moneylines(session, bdl, pending_ml_unlinked(session))
    settled = []
    by_game: dict[int, list] = defaultdict(list)
    for p in [*pending(session), *pending_with_game(session)]:
        if p.game_id:
            by_game[p.game_id].append(p)
    for game_id, preds in by_game.items():
        game = bdl.game(game_id)
        if str(game.get("status", "")).lower() != "final":
            continue
        props = [p for p in preds if getattr(p, "stat", None) != ML]
        for p in preds:
            if getattr(p, "stat", None) == ML:
                p.actual = _margin(p, game)
                p.status = "void" if p.actual is None else grade("over", 0, p.actual)
                p.settled_at = datetime.now(timezone.utc)
                settled.append(p)
        if not props:
            continue
        rows = bdl.game_stats(game_id)
        by_player = {r["player"]["id"]: r for r in rows}
        for p in props:
            row = by_player.get(p.player_id)
            if row is None or minutes(row.get("min")) == 0:
                # No jugó: la apuesta se anula en las casas, aquí también.
                p.status, p.actual = "void", None
            else:
                p.actual = float(row.get(p.stat) or 0)
                p.status = grade(p.side, p.line, p.actual)
            p.settled_at = datetime.now(timezone.utc)
            settled.append(p)
    session.commit()
    return settled + refresh_parlays(session)


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
