"""Suscripción con Stripe Checkout y webhook.

El acceso NUNCA se da al volver de Checkout: solo cuando Stripe lo confirma por
webhook (firmado). Así nadie se cuela con la URL de éxito.
El enlace de preventa (9 €, pago único) es aparte y no pasa por aquí.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .accounts import User

PLANS = ("monthly", "yearly")
TRIAL_DAYS = 7


def _stripe(secret_key: str):
    import stripe

    stripe.api_key = secret_key
    return stripe


def create_checkout(user: User, plan: str, *, secret_key: str, price_id: str, web_url: str) -> str:
    """Devuelve la URL de Stripe Checkout para suscribirse."""
    stripe = _stripe(secret_key)
    subscription_data: dict = {"metadata": {"user_id": str(user.id)}}
    if not user.trial_used:
        subscription_data["trial_period_days"] = TRIAL_DAYS
    params: dict = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "client_reference_id": str(user.id),
        "subscription_data": subscription_data,
        # Para los códigos de descuento (p. ej. a quien pagó la preventa).
        "allow_promotion_codes": True,
        "locale": "es",
        "success_url": f"{web_url}/cuenta?pago=ok",
        "cancel_url": f"{web_url}/cuenta",
        "metadata": {"user_id": str(user.id), "plan": plan},
    }
    if user.stripe_customer_id:
        params["customer"] = user.stripe_customer_id
    else:
        params["customer_email"] = user.email
    return stripe.checkout.Session.create(**params).url


def create_portal(user: User, *, secret_key: str, web_url: str) -> str:
    """Portal de cliente de Stripe: cambiar de plan, tarjeta, facturas y cancelar."""
    stripe = _stripe(secret_key)
    return stripe.billing_portal.Session.create(customer=user.stripe_customer_id, return_url=f"{web_url}/cuenta").url


def parse_webhook(payload: bytes, signature: str, webhook_secret: str) -> dict:
    """Comprueba la firma de Stripe. Lanza ValueError si no es válida."""
    import stripe

    try:
        stripe.WebhookSignature.verify_header(payload.decode(), signature, webhook_secret, tolerance=300)
    except stripe.SignatureVerificationError as exc:
        raise ValueError("Firma de Stripe no válida") from exc
    return json.loads(payload)


def _ts(value) -> datetime | None:
    return datetime.fromtimestamp(value, timezone.utc) if value else None


def _user_for(session: Session, obj: dict) -> User | None:
    user_id = (obj.get("metadata") or {}).get("user_id") or obj.get("client_reference_id")
    if user_id and str(user_id).isdigit():
        user = session.get(User, int(user_id))
        if user:
            return user
    customer = obj.get("customer")
    if customer:
        return session.scalar(select(User).where(User.stripe_customer_id == customer))
    return None


def apply_event(session: Session, event: dict) -> bool:
    """Actualiza la cuenta según el evento. Devuelve True si cambió algo."""
    kind = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    if kind == "checkout.session.completed" and obj.get("mode") == "subscription":
        user = _user_for(session, obj)
        if not user:
            return False
        user.stripe_customer_id = obj.get("customer") or user.stripe_customer_id
        session.commit()
        return True
    if kind.startswith("customer.subscription."):
        user = _user_for(session, obj)
        if not user:
            return False
        if obj.get("customer"):
            user.stripe_customer_id = obj["customer"]
        status = "canceled" if kind.endswith(".deleted") else obj.get("status")
        now = datetime.now(timezone.utc)
        if status == "trialing" and not user.trial_started_at:
            user.trial_started_at = now
        if status == "active" and not user.paid_at:
            user.paid_at = now
        if status == "canceled" and not user.canceled_at:
            user.canceled_at = now
        user.subscription_status = status
        # Desde 2025 Stripe pone el fin de periodo en cada elemento de la suscripción.
        items = (obj.get("items") or {}).get("data") or [{}]
        user.current_period_end = _ts(obj.get("current_period_end") or items[0].get("current_period_end"))
        user.cancel_at_period_end = bool(obj.get("cancel_at_period_end"))
        if obj.get("trial_end") or obj.get("status") in ("active", "trialing"):
            user.trial_used = True
        session.commit()
        return True
    return False
