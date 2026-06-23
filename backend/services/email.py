import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr

from backend.config import settings


logger = logging.getLogger(__name__)
SENT_EMAILS: list[dict] = []


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    text: str
    html: str | None = None


def clear_email_outbox():
    SENT_EMAILS.clear()


def sender_address():
    return formataddr((settings.email_from_name, settings.email_from_address))


def send_email(message: OutgoingEmail) -> bool:
    if settings.email_backend == "disabled":
        return False

    SENT_EMAILS.append(
        {
            "to": message.to,
            "subject": message.subject,
            "text": message.text,
            "html": message.html,
            "backend": settings.email_backend,
        }
    )

    if settings.email_backend == "console":
        logger.info(
            "Email transacional para %s | %s\n%s",
            message.to,
            message.subject,
            message.text,
        )
        return True

    if settings.email_backend != "smtp":
        logger.warning("EMAIL_BACKEND desconhecido: %s", settings.email_backend)
        return False

    if not settings.email_smtp_host:
        logger.warning("EMAIL_SMTP_HOST nao configurado")
        return False

    email_message = EmailMessage()
    email_message["From"] = sender_address()
    email_message["To"] = message.to
    email_message["Subject"] = message.subject
    email_message.set_content(message.text)
    if message.html:
        email_message.add_alternative(message.html, subtype="html")

    try:
        with smtplib.SMTP(settings.email_smtp_host, settings.email_smtp_port, timeout=10) as smtp:
            if settings.email_smtp_use_tls:
                smtp.starttls()
            if settings.email_smtp_username:
                smtp.login(settings.email_smtp_username, settings.email_smtp_password)
            smtp.send_message(email_message)
    except Exception:
        logger.exception("Falha ao enviar e-mail transacional para %s", message.to)
        return False
    return True
