"""Feed de mejores jugadas: tarjetas con lado, nota y probabilidad estimada.

Por qué tarjetas guardadas y no calculadas al vuelo: lo que se enseña antes del partido queda
registrado tal cual (con su hash) y se liquida solo, así el historial del feed es verificable y
no cambia si mañana cambia la fórmula de la nota. Las tarjetas salen de las líneas publicadas
(board.publish_board) cuya nota llega a FEED_MIN_SCORE.

No es una recomendación: es el resumen de los datos de cada línea (ver nota.py).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base, Prediction, content_hash
from .nota import nota

# Nota mínima para salir en el feed (con los datos de 2025-26, ~1 de cada 9 líneas).
FEED_MIN_SCORE = 60


class FeedCard(Base):
    __tablename__ = "feed_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prediction_id: Mapped[int] = mapped_column(Integer, index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    game_date: Mapped[str] = mapped_column(String(10), index=True)
    game_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    player_id: Mapped[int] = mapped_column(Integer)
    player_name: Mapped[str] = mapped_column(String(120))
    stat: Mapped[str] = mapped_column(String(10))
    line: Mapped[float] = mapped_column(Float)
    side: Mapped[str] = mapped_column(String(5))
    score: Mapped[int] = mapped_column(Integer)
    prob: Mapped[float] = mapped_column(Float)  # probabilidad estimada del lado
    fair: Mapped[float] = mapped_column(Float)  # precio justo del lado (no se enseña; para medir)
    reasons: Mapped[list] = mapped_column(JSON)
    nota_version: Mapped[str] = mapped_column(String(20))
    content_hash: Mapped[str] = mapped_column(String(64))
    # pending | won | lost | push | void
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)
    actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def publish_cards(session: Session, predictions: list[Prediction], now: datetime | None = None) -> list[FeedCard]:
    """Crea las tarjetas de las líneas recién publicadas que llegan a la nota mínima.
    Las predicciones deben tener id (haber pasado por flush)."""
    now = now or datetime.now(timezone.utc)
    cards = []
    for p in predictions:
        n = nota(p.analysis or {})
        if n is None or n.score < FEED_MIN_SCORE:
            continue
        record = {"prediction_id": p.id, "game_date": p.game_date, "player_id": p.player_id,
                  "player_name": p.player_name, "stat": p.stat, "line": p.line, "side": n.side,
                  "score": n.score, "prob": n.prob, "nota_version": n.version}
        card = FeedCard(**record, published_at=now, game_id=p.game_id, event_id=p.event_id, fair=n.fair,
                        reasons=n.reasons, content_hash=content_hash({**record, "published_at": now.isoformat()}))
        session.add(card)
        cards.append(card)
    return cards


def pending_cards(session: Session) -> list[FeedCard]:
    return list(session.scalars(select(FeedCard).where(FeedCard.status == "pending")))


def cards_for(session: Session, game_date: str) -> list[tuple[FeedCard, Prediction]]:
    stmt = (select(FeedCard, Prediction).join(Prediction, Prediction.id == FeedCard.prediction_id)
            .where(FeedCard.game_date == game_date))
    return [(card, pred) for card, pred in session.execute(stmt)]


def public_card(card: FeedCard, pred: Prediction, unlocked: bool) -> dict:
    """Tarjeta para la web. Bloqueada (sin suscripción y antes del partido): solo la nota y el
    partido, ni jugador ni lado."""
    from .board import game_header

    out = {"id": card.id, "score": card.score, "stat": card.stat, "game": game_header(pred),
           "status": card.status, "locked": not unlocked}
    if unlocked:
        out.update(player=card.player_name, line=card.line, side=card.side, prob=card.prob,
                   reasons=card.reasons, actual=card.actual, line_id=pred.id, content_hash=card.content_hash)
    return out


def summary(session: Session) -> dict:
    """Cómo le ha ido al feed: acierto frente a la probabilidad que dijo (debería parecerse)."""
    settled = list(session.scalars(select(FeedCard).where(FeedCard.status.in_(("won", "lost")))))
    won = sum(c.status == "won" for c in settled)
    return {
        "settled": len(settled),
        "won": won,
        "lost": len(settled) - won,
        "hit_rate": round(won / len(settled), 4) if settled else None,
        "avg_prob": round(sum(c.prob for c in settled) / len(settled), 4) if settled else None,
    }
