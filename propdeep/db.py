"""Historial público de predicciones.

Regla del producto: todo lo publicado queda registrado, gane o pierda. Una vez
publicada, una predicción no se edita; solo se liquida con el resultado real.
El hash del contenido permite comprobar que nadie la ha tocado después.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


class Base(DeclarativeBase):
    pass


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    game_date: Mapped[str] = mapped_column(String(10), index=True)
    game_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player_id: Mapped[int] = mapped_column(Integer)
    player_name: Mapped[str] = mapped_column(String(120))
    stat: Mapped[str] = mapped_column(String(10))
    line: Mapped[float] = mapped_column(Float)
    side: Mapped[str | None] = mapped_column(String(5), nullable=True)  # None = sin ventaja
    odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    bookmaker: Mapped[str | None] = mapped_column(String(60), nullable=True)
    prob: Mapped[float] = mapped_column(Float)  # probabilidad del lado elegido (o del over)
    edge: Mapped[float] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(20))
    report: Mapped[str] = mapped_column(Text)
    analysis: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    # pending | won | lost | push | void | no_bet
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)
    actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


def make_session_factory(url: str) -> sessionmaker[Session]:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    # Railway entrega URLs "postgres://"; usamos el driver psycopg 3.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg://" + url[len(prefix):]
    engine = create_engine(url, connect_args=connect_args)
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


def content_hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def publish(session: Session, *, analysis: dict, report: str, meta: dict) -> Prediction:
    side = analysis["side"]
    p_over = analysis["prob_over_final"]
    record = {
        "game_date": meta["game_date"],
        "game_id": meta.get("game_id"),
        "player_id": meta["player_id"],
        "player_name": analysis["player"],
        "stat": analysis["stat"],
        "line": analysis["line"],
        "side": side,
        "odds": analysis["odds_taken"],
        "bookmaker": meta.get("bookmaker"),
        "prob": p_over if side != "under" else 1 - p_over,
        "edge": analysis["edge"],
        "confidence": analysis["confidence"],
        "report": report,
    }
    published_at = datetime.now(timezone.utc)
    prediction = Prediction(
        **record,
        analysis=analysis,
        published_at=published_at,
        status="pending" if side else "no_bet",
        content_hash=content_hash({**record, "published_at": published_at.isoformat()}),
    )
    session.add(prediction)
    session.commit()
    return prediction


def pending(session: Session) -> list[Prediction]:
    return list(session.scalars(select(Prediction).where(Prediction.status == "pending")))


def all_predictions(session: Session, limit: int = 500) -> list[Prediction]:
    stmt = select(Prediction).order_by(Prediction.published_at.desc()).limit(limit)
    return list(session.scalars(stmt))
