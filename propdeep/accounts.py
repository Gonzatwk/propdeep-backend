"""Cuentas mínimas: solo el correo, con acceso por enlace mágico (sin contraseña).

RGPD: guardamos lo imprescindible. El correo, el id de cliente de Stripe y el estado
de la suscripción. Nada de nombre, teléfono ni datos de pago (eso lo guarda Stripe).
Los tokens se guardan como hash: con una copia de la base no se puede entrar.
"""
from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, delete, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from .db import Base

LOGIN_TTL = timedelta(minutes=20)
SESSION_TTL = timedelta(days=60)
MAX_LOGINS_PER_HOUR = 5
# Estados de Stripe que dan acceso. "past_due": Stripe está reintentando el cobro.
ACTIVE_STATUSES = {"active", "trialing", "past_due"}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stripe_customer_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    subscription_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    # La prueba gratuita de 7 días solo se da una vez por cuenta.
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False)
    # Métrica de validación: cuántos empiezan la prueba y cuántos pasan a pago.
    trial_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WaitlistEntry(Base):
    """Correos de la landing para avisar del lanzamiento. Solo el correo y la fecha."""

    __tablename__ = "waitlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(String(40), nullable=True)


class LoginToken(Base):
    __tablename__ = "login_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Se marca en vez de borrarse para que cuente en el límite de intentos.
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RateLimited(Exception):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    # SQLite devuelve fechas sin zona horaria aunque se guarden con ella.
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def normalize_email(email: str) -> str | None:
    email = (email or "").strip().lower()
    return email if len(email) <= 254 and EMAIL_RE.match(email) else None


def request_login(session: Session, email: str) -> str:
    """Crea un token de acceso de un solo uso y lo devuelve (para mandarlo por correo)."""
    now = _now()
    session.execute(delete(LoginToken).where(LoginToken.expires_at < now))
    recent = session.scalar(
        select(func.count()).select_from(LoginToken)
        .where(LoginToken.email == email, LoginToken.created_at > now - timedelta(hours=1))
    )
    if recent >= MAX_LOGINS_PER_HOUR:
        session.commit()
        raise RateLimited
    token = secrets.token_urlsafe(32)
    session.add(LoginToken(email=email, token_hash=_hash(token), created_at=now, expires_at=now + LOGIN_TTL))
    session.commit()
    return token


def verify_login(session: Session, token: str) -> tuple[User, str] | None:
    """Canjea el token del enlace por una sesión. Crea la cuenta la primera vez."""
    row = session.scalar(select(LoginToken).where(LoginToken.token_hash == _hash(token or "")))
    if row is None or row.used or _aware(row.expires_at) < _now():
        return None
    email = row.email
    row.used = True
    user = session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, created_at=_now())
        session.add(user)
        session.flush()
    session_token = secrets.token_urlsafe(32)
    session.add(AuthSession(user_id=user.id, token_hash=_hash(session_token), expires_at=_now() + SESSION_TTL))
    session.commit()
    return user, session_token


def user_from_token(session: Session, token: str) -> User | None:
    if not token:
        return None
    row = session.scalar(select(AuthSession).where(AuthSession.token_hash == _hash(token)))
    if row is None or _aware(row.expires_at) < _now():
        return None
    return session.get(User, row.user_id)


def logout(session: Session, token: str) -> None:
    session.execute(delete(AuthSession).where(AuthSession.token_hash == _hash(token or "")))
    session.commit()


def join_waitlist(session: Session, email: str, source: str | None = None) -> None:
    if session.scalar(select(WaitlistEntry).where(WaitlistEntry.email == email)) is None:
        session.add(WaitlistEntry(email=email, created_at=_now(), source=source))
        session.commit()


def metrics(session: Session) -> dict:
    """Embudo de validación: prueba gratis -> pago."""
    users = session.scalars(select(User)).all()
    trials = [u for u in users if u.trial_started_at]
    paid = [u for u in users if u.paid_at]
    return {
        "accounts": len(users),
        "waitlist": session.scalar(select(func.count()).select_from(WaitlistEntry)),
        "trials_started": len(trials),
        "trials_in_progress": sum(1 for u in users if u.subscription_status == "trialing"),
        "paid": len(paid),
        "paid_after_trial": sum(1 for u in paid if u.trial_started_at),
        "trial_to_paid": round(sum(1 for u in paid if u.trial_started_at) / len(trials), 3) if trials else None,
        "active_subscribers": sum(1 for u in users if is_subscriber(u) and u.subscription_status != "trialing"),
        "canceled": sum(1 for u in users if u.canceled_at),
    }


def delete_user(session: Session, user: User) -> None:
    from .chat import ChatUsage

    session.execute(delete(ChatUsage).where(ChatUsage.user_id == user.id))
    session.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
    session.execute(delete(LoginToken).where(LoginToken.email == user.email))
    session.delete(user)
    session.commit()


def is_subscriber(user: User | None) -> bool:
    if user is None or user.subscription_status not in ACTIVE_STATUSES:
        return False
    end = _aware(user.current_period_end)
    # Un día de margen por si el webhook de renovación llega tarde.
    return end is None or end + timedelta(days=1) > _now()


def public_user(user: User) -> dict:
    end = _aware(user.current_period_end)
    return {
        "email": user.email,
        "subscriber": is_subscriber(user),
        "status": user.subscription_status,
        "current_period_end": end.isoformat() if end else None,
        "cancel_at_period_end": user.cancel_at_period_end,
        "trial_available": not user.trial_used,
        "has_billing": bool(user.stripe_customer_id),
    }
