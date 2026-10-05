"""Liquidación de predicciones y rendimiento real del historial."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .clients.balldontlie import BalldontlieClient, minutes
from .db import Prediction, pending


def grade(side: str, line: float, actual: float) -> str:
    if actual == line:
        return "push"
    went_over = actual > line
    return "won" if went_over == (side == "over") else "lost"


def settle(session: Session, bdl: BalldontlieClient) -> list:
    """Liquida las predicciones y los picks pendientes cuyo partido ya tiene estadísticas finales."""
    from .picks import pending_with_game

    settled = []
    by_game: dict[int, list] = defaultdict(list)
    for p in [*pending(session), *pending_with_game(session)]:
        if p.game_id:
            by_game[p.game_id].append(p)
    for game_id, preds in by_game.items():
        if str(bdl.game(game_id).get("status", "")).lower() != "final":
            continue
        rows = bdl.game_stats(game_id)
        by_player = {r["player"]["id"]: r for r in rows}
        for p in preds:
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
    return settled


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
    by_conf = defaultdict(list)
    for p in picks:
        by_conf[p.confidence].append(p)
    return {
        "overall": block(picks),
        "by_confidence": {k: block(v) for k, v in sorted(by_conf.items())},
        "no_bet_analyses": sum(1 for p in predictions if not p.side),
    }
