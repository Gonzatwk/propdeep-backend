"""Suscripción con Stripe Checkout y webhook.

El acceso NUNCA se da al volver de Checkout: solo cuando Stripe lo confirma por
webhook (firmado). Así nadie se cuela con la URL de éxito.
Planes: mensual, anual y Pro (suscripciones con prueba de 7 días) y el pase de 7 días
(pago único, sin renovación ni prueba).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .accounts import User

PLANS = ("monthly", "yearly", "pro", "pass")
TRIAL_DAYS = 7
PASS_DAYS = 7
PAUSE_DAYS = 30


def _stripe(secret_key: str):
    import stripe

    stripe.api_key = secret_key
    return stripe


def create_checkout(user: User, plan: str, *, secret_key: str, price_id: str, web_url: str) -> str:
    """Devuelve la URL de Stripe Checkout para suscribirse o comprar el pase."""
    stripe = _stripe(secret_key)
    params: dict = {
        "line_items": [{"price": price_id, "quantity": 1}],
        "client_reference_id": str(user.id),
        "allow_promotion_codes": True,
        "locale": "es",
        "success_url": f"{web_url}/cuenta?pago=ok",
        "cancel_url": f"{web_url}/cuenta",
        "metadata": {"user_id": str(user.id), "plan": plan},
    }
    if plan == "pass":
        params["mode"] = "payment"
        params["payment_intent_data"] = {"metadata": {"user_id": str(user.id), "plan": plan}}
    else:
        subscription_data: dict = {"metadata": {"user_id": str(user.id), "plan": plan}}
        if not user.trial_used:
            subscription_data["trial_period_days"] = TRIAL_DAYS
        params["mode"] = "subscription"
        params["subscription_data"] = subscription_data
    if user.stripe_customer_id:
        params["customer"] = user.stripe_customer_id
    elif plan == "pass":
        # En un pago único Stripe no crea cliente si no se le pide; lo queremos para las facturas.
        params["customer_email"] = user.email
        params["customer_creation"] = "always"
    else:
        params["customer_email"] = user.email
    return stripe.checkout.Session.create(**params).url


def pause(user: User, *, secret_key: str, now: datetime | None = None) -> datetime:
    """Pausa los cobros PAUSE_DAYS días en vez de cancelar. Sin cobro, sin acceso.
    Stripe la reanuda sola en la fecha; también se puede reanudar antes."""
    stripe = _stripe(secret_key)
    resumes = (now or datetime.now(timezone.utc)) + timedelta(days=PAUSE_DAYS)
    stripe.Subscription.modify(
        user.stripe_subscription_id,
        pause_collection={"behavior": "void", "resumes_at": int(resumes.timestamp())},
    )
    return resumes


def resume(user: User, *, secret_key: str) -> None:
    stripe = _stripe(secret_key)
    stripe.Subscription.modify(user.stripe_subscription_id, pause_collection="")


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


def _plan(obj: dict, plans_by_price: dict[str, str]) -> str | None:
    """El plan sale del precio (así cuenta un cambio de plan desde el portal)."""
    for item in (obj.get("items") or {}).get("data") or []:
        price = (item.get("price") or {}).get("id")
        if price in plans_by_price:
            return plans_by_price[price]
    plan = (obj.get("metadata") or {}).get("plan")
    return plan if plan in ("monthly", "yearly", "pro") else None


def apply_event(session: Session, event: dict, plans_by_price: dict[str, str] | None = None) -> bool:
    """Actualiza la cuenta según el evento. Devuelve True si cambió algo."""
    kind = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}
    if kind == "checkout.session.completed" and obj.get("mode") == "payment":
        # Pase de 7 días: solo si está pagado (con tarjeta lo está ya al completar).
        if (obj.get("metadata") or {}).get("plan") != "pass" or obj.get("payment_status") != "paid":
            return False
        user = _user_for(session, obj)
        if not user:
            return False
        user.stripe_customer_id = obj.get("customer") or user.stripe_customer_id
        now = datetime.now(timezone.utc)
        current = user.pass_until.replace(tzinfo=timezone.utc) if user.pass_until and user.pass_until.tzinfo is None else user.pass_until
        user.pass_until = max(now, current or now) + timedelta(days=PASS_DAYS)
        session.commit()
        return True
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
        # Con los cobros en pausa Stripe la sigue dando por "active": para nosotros no da acceso.
        pause_info = obj.get("pause_collection") or {}
        if status == "active" and pause_info:
            status = "paused"
        user.paused_until = _ts(pause_info.get("resumes_at")) if pause_info else None
        if obj.get("id"):
            user.stripe_subscription_id = obj["id"]
        user.plan = _plan(obj, plans_by_price or {}) or user.plan
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
