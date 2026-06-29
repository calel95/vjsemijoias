import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formataddr

from sqlalchemy import select

from backend.config import settings
from backend.database import SessionLocal
from backend.models import StoreSetting


logger = logging.getLogger(__name__)
SENT_EMAILS: list[dict] = []
EMAIL_SETTING_KEYS = {
    "EMAIL_BACKEND",
    "EMAIL_FROM_NAME",
    "EMAIL_FROM_ADDRESS",
    "EMAIL_SMTP_HOST",
    "EMAIL_SMTP_PORT",
    "EMAIL_SMTP_USERNAME",
    "EMAIL_SMTP_PASSWORD",
    "EMAIL_SMTP_USE_TLS",
}


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    text: str
    html: str | None = None


@dataclass(frozen=True)
class EmailRuntimeConfig:
    backend: str
    from_name: str
    from_address: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool


def clear_email_outbox():
    SENT_EMAILS.clear()


def parse_bool(value) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on", "sim"}


def load_email_overrides() -> dict[str, str]:
    try:
        with SessionLocal() as db:
            rows = db.scalars(select(StoreSetting).where(StoreSetting.key.in_(EMAIL_SETTING_KEYS))).all()
            return {row.key: row.value for row in rows}
    except Exception:
        logger.debug("Nao foi possivel carregar configuracoes de e-mail do banco", exc_info=True)
        return {}


def current_email_config() -> EmailRuntimeConfig:
    overrides = load_email_overrides()
    try:
        smtp_port = int(overrides.get("EMAIL_SMTP_PORT") or settings.email_smtp_port)
    except (TypeError, ValueError):
        smtp_port = settings.email_smtp_port
    return EmailRuntimeConfig(
        backend=(overrides.get("EMAIL_BACKEND") or settings.email_backend).strip().lower(),
        from_name=(overrides.get("EMAIL_FROM_NAME") or settings.email_from_name).strip(),
        from_address=(overrides.get("EMAIL_FROM_ADDRESS") or settings.email_from_address).strip(),
        smtp_host=(overrides.get("EMAIL_SMTP_HOST") or settings.email_smtp_host).strip(),
        smtp_port=smtp_port,
        smtp_username=(overrides.get("EMAIL_SMTP_USERNAME") or settings.email_smtp_username).strip(),
        smtp_password=overrides.get("EMAIL_SMTP_PASSWORD") or settings.email_smtp_password,
        smtp_use_tls=parse_bool(overrides.get("EMAIL_SMTP_USE_TLS", settings.email_smtp_use_tls)),
    )


def sender_address(email_config: EmailRuntimeConfig | None = None):
    active_config = email_config or current_email_config()
    return formataddr((active_config.from_name, active_config.from_address))


def send_email(message: OutgoingEmail) -> bool:
    email_config = current_email_config()
    if email_config.backend == "disabled":
        return False

    SENT_EMAILS.append(
        {
            "to": message.to,
            "subject": message.subject,
            "text": message.text,
            "html": message.html,
            "backend": email_config.backend,
            "from": sender_address(email_config),
        }
    )

    if email_config.backend == "console":
        logger.info(
            "Email transacional para %s | %s\n%s",
            message.to,
            message.subject,
            message.text,
        )
        return True

    if email_config.backend != "smtp":
        logger.warning("EMAIL_BACKEND desconhecido: %s", email_config.backend)
        return False

    if not email_config.smtp_host:
        logger.warning("EMAIL_SMTP_HOST nao configurado")
        return False

    email_message = EmailMessage()
    email_message["From"] = sender_address(email_config)
    email_message["To"] = message.to
    email_message["Subject"] = message.subject
    email_message.set_content(message.text)
    if message.html:
        email_message.add_alternative(message.html, subtype="html")

    try:
        with smtplib.SMTP(email_config.smtp_host, email_config.smtp_port, timeout=10) as smtp:
            if email_config.smtp_use_tls:
                smtp.starttls()
            if email_config.smtp_username:
                smtp.login(email_config.smtp_username, email_config.smtp_password)
            smtp.send_message(email_message)
    except Exception:
        logger.exception("Falha ao enviar e-mail transacional para %s", message.to)
        return False
    return True