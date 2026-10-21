"""Paper bets: un bank simulado en euros para practicar sin arriesgar dinero.

Separado de «Mis picks» (que es el historial que no se toca): aquí el stake va en euros,
las apuestas sueltas son picks con `paper=True` y las combinadas, parlays con `paper=True`.
Se liquidan igual que el resto (solas, con el resultado real). «Empezar de cero» no borra
nada: cuenta solo lo apostado desde ese momento.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base
from .picks import Parlay, Pick, _aware, all_parlays, public, public_parlay

DEFAULT_BANK = 500.0
# Importe sugerido: un porcentaje fijo del bank actual (apuesta plana, sin subir al ganar).
SUGGESTED_PCT = 0.02


class PaperBank(Base):
    __tablename__ = "paper_bank"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    initial: Mapped[float] = mapped_column(Float)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def bank(session: Session) -> PaperBank:
    row = session.get(PaperBank, 1)
    if row is None:
        # Sin bank todavía: cuenta todo lo apostado hasta ahora.
        row = PaperBank(id=1, initial=DEFAULT_BANK, started_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
        session.add(row)
        session.commit()
    return row


def set_bank(session: Session, initial: float, reset: bool = False) -> PaperBank:
    row = bank(session)
    row.initial = float(initial)
    if reset:
        row.started_at = datetime.now(timezone.utc)
    session.commit()
    return row


def _bets(session: Session, since: datetime) -> list[dict]:
    """Apuestas (sueltas y combinadas) desde `since`, en una sola lista."""
    singles = session.scalars(select(Pick).where(Pick.paper.is_(True), Pick.parlay_id.is_(None))).all()
    out = [{"kind": "single", "obj": p, "public": public(p), "odds": p.odds} for p in singles]
    for p, legs in all_parlays(session, paper=True):
        out.append({"kind": "parlay", "obj": p, "public": public_parlay(p, legs), "odds": p.settled_odds or p.odds})
    since = _aware(since)
    return [b for b in out if _aware(b["obj"].published_at) >= since]


def _profit(b: dict) -> float:
    o = b["obj"]
    if o.status == "won":
        return o.stake * ((getattr(o, "settled_odds", None) or o.odds) - 1)
    if o.status == "lost":
        return -o.stake
    return 0.0


def state(session: Session) -> dict:
    row = bank(session)
    bets = _bets(session, row.started_at)
    settled = sorted((b for b in bets if b["obj"].status in ("won", "lost", "push", "void")),
                     key=lambda b: (_aware(b["obj"].settled_at or b["obj"].published_at), b["obj"].id))
    pending = [b for b in bets if b["obj"].status == "pending"]

    # La gráfica arranca con la primera apuesta (o ahora), no en una fecha vacía.
    first = min((_aware(b["obj"].published_at) for b in bets), default=datetime.now(timezone.utc))
    start = max(_aware(row.started_at), first) if bets else first
    current, curve = row.initial, [{"t": start.isoformat(), "bank": round(row.initial, 2)}]
    peak, max_dd, streak, worst = row.initial, 0.0, 0, 0
    for b in settled:
        current += _profit(b)
        curve.append({"t": _aware(b["obj"].settled_at or b["obj"].published_at).isoformat(), "bank": round(current, 2)})
        peak = max(peak, current)
        max_dd = max(max_dd, peak - current)
        if b["obj"].status == "lost":
            streak += 1
            worst = max(worst, streak)
        elif b["obj"].status == "won":
            streak = 0

    graded = [b for b in settled if b["obj"].status in ("won", "lost")]
    staked = sum(b["obj"].stake for b in graded)
    profit = current - row.initial
    at_risk = sum(b["obj"].stake for b in pending)
    available = current - at_risk
    rows = sorted(bets, key=lambda b: (_aware(b["obj"].published_at), b["obj"].id), reverse=True)
    return {
        "bank": {
            "initial": round(row.initial, 2),
            "started_at": _aware(row.started_at).isoformat(),
            "current": round(current, 2),
            "available": round(available, 2),
            "at_risk": round(at_risk, 2),
            "profit": round(profit, 2),
            "roi": round(profit / staked, 4) if staked else None,
            "hit_rate": round(sum(b["obj"].status == "won" for b in graded) / len(graded), 4) if graded else None,
            "won": sum(b["obj"].status == "won" for b in graded),
            "lost": sum(b["obj"].status == "lost" for b in graded),
            "pending": len(pending),
            "worst_losing_streak": worst,
            "max_drawdown": round(max_dd, 2),
        },
        "suggested": {"pct": SUGGESTED_PCT, "stake": max(round(available * SUGGESTED_PCT * 2) / 2, 0.0)},
        "curve": curve,
        "bets": [{**b["public"], "kind": b["kind"], "profit": round(_profit(b), 2),
                  "potential_return": round(b["obj"].stake * b["odds"], 2)} for b in rows],
    }


def cancel(session: Session, kind: str, bet_id: int, now: datetime | None = None) -> None:
    """Quita una paper bet sin liquidar (para corregir un error al apuntarla)."""
    now = now or datetime.now(timezone.utc)
    if kind == "single":
        bet = session.get(Pick, bet_id)
        legs = [bet] if bet is not None and bet.paper and bet.parlay_id is None else []
    else:
        bet = session.get(Parlay, bet_id)
        legs = list(session.scalars(select(Pick).where(Pick.parlay_id == bet_id))) if bet is not None and bet.paper else []
    if not legs:
        raise LookupError("Apuesta no encontrada")
    if bet.status != "pending":
        raise ValueError("Ya está liquidada: no se puede quitar")
    for leg in legs:
        session.delete(leg)
    if kind == "parlay":
        session.delete(bet)
    session.commit()
