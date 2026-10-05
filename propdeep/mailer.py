"""Envío del enlace de acceso por correo (SMTP). Sin SMTP configurado, lo deja en el log."""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

log = logging.getLogger(__name__)


def send_login_link(settings, to: str, link: str) -> None:
    if not settings.smtp_host:
        log.warning("SMTP sin configurar. Enlace de acceso para %s: %s", to, link)
        return
    msg = EmailMessage()
    msg["Subject"] = "Tu enlace para entrar en PropDeep"
    msg["From"] = settings.mail_from or settings.smtp_user
    msg["To"] = to
    msg.set_content(
        "Hola:\n\n"
        "Pulsa este enlace para entrar en PropDeep. Caduca en 20 minutos y solo sirve una vez:\n\n"
        f"{link}\n\n"
        "Si no lo has pedido tú, ignora este correo.\n\n"
        "PropDeep · Análisis estadístico de player props de la NBA. Solo mayores de 18 años.\n"
    )
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except Exception:  # noqa: BLE001 - un fallo de correo no debe tumbar la API
        log.exception("No se pudo enviar el enlace de acceso a %s", to)
