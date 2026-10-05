"""Envío del enlace de acceso por correo (SMTP). Sin SMTP configurado, lo deja en el log."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)


FOOTER = "PropDeep · Análisis estadístico de player props de la NBA. Solo mayores de 18 años.\n"
PLAN_NAMES = {"monthly": "mensual", "yearly": "anual", "pro": "Pro"}


def _send(settings, to: str, subject: str, body: str) -> bool:
    """Devuelve True si el correo salió (o, sin SMTP, si quedó en el log)."""
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


def send_trial_reminder(settings, to: str, *, ends: str, plan: str | None, lines: int, games: int) -> bool:
    """Día 5 de la prueba: qué ha tenido estos días y cuándo se cobra. Cancelar, a un clic."""
    plan_txt = f"el plan {PLAN_NAMES[plan]}" if plan in PLAN_NAMES else "tu plan"
    used = (f"Estos días PropDeep ha analizado {lines} líneas de {games} partidos, todas a tu alcance.\n\n"
            if lines else "")
    return _send(settings, to, f"Tu prueba de PropDeep acaba el {ends}", (
        "Hola:\n\n"
        f"Te escribimos para que no te pille por sorpresa: tu prueba gratis acaba el {ends} "
        f"y ese día se cobrará {plan_txt}.\n\n"
        + used +
        "Si te está sirviendo, no tienes que hacer nada. Si no, cancélala antes de esa fecha desde "
        f"Mi cuenta > Gestionar suscripción ({settings.web_url}/cuenta) y no pagarás nada.\n\n"
        "Recuerda: es información estadística, no garantiza ganar. Juega solo lo que puedas permitirte "
        "perder (jugarbien.es).\n\n" + FOOTER
    ))
