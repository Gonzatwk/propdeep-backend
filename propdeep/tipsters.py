"""Auditoría de tipsters: el rendimiento real de los picks que publican en abierto.

Para que sea legal (Ley 3/1991, art. 9) y creíble, todo tiene que ser exacto y verificable:
- Solo picks publicados en abierto ANTES del partido, cada uno con su prueba (enlace o captura).
- Se registran todos los que se ven, no se editan ni se borran; solo se liquidan una vez.
- Se publican números, sin opiniones. Hasta TIPSTERS_PUBLIC=true solo los ve el autor.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base, content_hash
from .picks import summary

RESULTS = ("won", "lost", "push", "void")


class Tipster(Base):
    __tablename__ = "tipsters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    # Dónde publica (canal de Telegram, perfil de X...): para que cualquiera lo compruebe.
    url: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TipsterPick(Base):
    __tablename__ = "tipster_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipster_id: Mapped[int] = mapped_column(ForeignKey("tipsters.id"), index=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # cuándo lo publicó él
    event_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    event: Mapped[str] = mapped_column(String(160))  # "Lakers - Celtics"
    selection: Mapped[str] = mapped_column(String(200))  # "LeBron más de 24,5 puntos"
    odds: Mapped[float] = mapped_column(Float)
    stake: Mapped[float] = mapped_column(Float, default=1.0)  # unidades que dijo él (1 si no lo dijo)
    evidence_url: Mapped[str] = mapped_column(String(500))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TipsterError(ValueError):
    pass


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def _iso(dt: datetime | None) -> str | None:
    dt = _aware(dt)
    return dt.isoformat() if dt else None


def add_tipster(session: Session, name: str, url: str) -> Tipster:
    name = name.strip()
    if session.scalar(select(Tipster).where(Tipster.name == name)):
        raise TipsterError("Ese tipster ya está")
    t = Tipster(name=name, url=url.strip(), created_at=datetime.now(timezone.utc))
    session.add(t)
    session.commit()
    return t


def add_pick(session: Session, tipster_id: int, data: dict) -> TipsterPick:
    if session.get(Tipster, tipster_id) is None:
        raise LookupError("Tipster no encontrado")
    posted, start = _aware(data["posted_at"]), _aware(data["event_start"])
    if posted >= start:
        raise TipsterError("Solo cuentan los picks publicados antes de que empiece el partido")
    if not str(data.get("evidence_url") or "").startswith(("http://", "https://")):
        raise TipsterError("Falta el enlace a la prueba (el mensaje o la captura)")
    now = datetime.now(timezone.utc)
    record = {
        "tipster_id": tipster_id,
        "posted_at": posted.isoformat(),
        "event_start": start.isoformat(),
        "event": data["event"].strip(),
        "selection": data["selection"].strip(),
        "odds": data["odds"],
        "stake": data.get("stake") or 1.0,
        "evidence_url": data["evidence_url"].strip(),
    }
    p = TipsterPick(**{**record, "posted_at": posted, "event_start": start}, recorded_at=now,
                    content_hash=content_hash({**record, "recorded_at": now.isoformat()}))
    session.add(p)
    session.commit()
    return p


def settle(session: Session, pick_id: int, result: str, now: datetime | None = None) -> TipsterPick:
    p = session.get(TipsterPick, pick_id)
    if p is None:
        raise LookupError("Pick no encontrado")
    if p.status != "pending":
        raise TipsterError("Ese pick ya tiene resultado y no se cambia")
    if result not in RESULTS:
        raise TipsterError("Resultado no válido")
    now = now or datetime.now(timezone.utc)
    if _aware(p.event_start) > now:
        raise TipsterError("El partido aún no ha empezado")
    p.status, p.settled_at = result, now
    session.commit()
    return p


def public_pick(p: TipsterPick) -> dict:
    return {
        "id": p.id,
        "posted_at": _iso(p.posted_at),
        "event_start": _iso(p.event_start),
        "event": p.event,
        "selection": p.selection,
        "odds": p.odds,
        "stake": p.stake,
        "evidence_url": p.evidence_url,
        "recorded_at": _iso(p.recorded_at),
        "status": p.status,
        "content_hash": p.content_hash,
    }


def report(session: Session) -> list[dict]:
    """Cada tipster con su resumen (mismo cálculo que los picks del autor) y sus picks."""
    out = []
    for t in session.scalars(select(Tipster).order_by(Tipster.name)):
        ps = list(session.scalars(select(TipsterPick).where(TipsterPick.tipster_id == t.id)
                                  .order_by(TipsterPick.posted_at.desc())))
        out.append({"id": t.id, "name": t.name, "url": t.url, "since": _iso(t.created_at),
                    "summary": summary(ps), "picks": [public_pick(p) for p in ps]})
    return out
