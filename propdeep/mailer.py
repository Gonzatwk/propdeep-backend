"""Envío de correos: Resend (HTTPS) si hay RESEND_API_KEY, si no SMTP; sin nada, al log.

Railway (plan Hobby) bloquea el SMTP saliente, así que en producción se usa Resend.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

import httpx

log = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"
FOOTER = "PropDeep · Análisis estadístico de player props de la NBA. Solo mayores de 18 años.\n"


def _send_resend(settings, to: str, subject: str, body: str) -> bool:
    if not settings.mail_from:
        log.error("Falta MAIL_FROM (una dirección del dominio verificado en Resend)")
        return False
    try:
        r = httpx.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={"from": settings.mail_from, "to": [to], "subject": subject, "text": body},
            timeout=20,
        )
        r.raise_for_status()
        return True
    except httpx.HTTPError as exc:
        detail = exc.response.text[:300] if isinstance(exc, httpx.HTTPStatusError) else exc
        log.error("Resend no envió «%s» a %s: %s", subject, to, detail)
        return False


def _send(settings, to: str, subject: str, body: str) -> bool:
    """Devuelve True si el correo salió (o, sin correo configurado, si quedó en el log)."""
    if settings.resend_api_key:
        return _send_resend(settings, to, subject, body)
    if not settings.smtp_host:
        log.warning("SMTP sin configurar. Correo para %s (%s):\n%s", to, subject, body)
        return True
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.mail_from or settings.smtp_user
    msg["To"] = to
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
        return True
    except Exception:  # noqa: BLE001 - un fallo de correo no debe tumbar la API
        log.exception("No se pudo enviar «%s» a %s", subject, to)
        return False


def send_login_link(settings, to: str, link: str) -> None:
    _send(settings, to, "Tu enlace para entrar en PropDeep", (
        "Hola:\n\n"
        "Pulsa este enlace para entrar en PropDeep. Caduca en 20 minutos y solo sirve una vez:\n\n"
        f"{link}\n\n"
        "Si no lo has pedido tú, ignora este correo.\n\n" + FOOTER
    ))
