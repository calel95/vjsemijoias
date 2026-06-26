import os
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import FRONTEND_ROOT, env_bool, settings
from backend.models import Coupon, StoreSetting
from backend.services.validation import clean_text, digits_only, normalize_email, normalize_phone


def env_value(name, default=""):
    return os.getenv(name, default).strip()


def env_int(name, default):
    try:
        return int(env_value(name, str(default)) or default)
    except ValueError:
        return default


def money_value(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Valor monetario invalido") from exc


def bool_text(value):
    return "true" if bool(value) else "false"


def parse_bool(value):
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "sim"}


@dataclass(frozen=True)
class BrandSettings:
    name: str = env_value("STORE_NAME", "VJ Semijoias")
    short_name: str = env_value("STORE_SHORT_NAME", "VJ")
    tagline: str = env_value("STORE_TAGLINE", "SEMIJOIAS")
    description: str = env_value(
        "STORE_DESCRIPTION",
        "Semijoias finas banhadas a ouro 18k.",
    )
    slogan: str = env_value("STORE_SLOGAN", "Brilhe em cada momento")
    logo_path: str = env_value("STORE_LOGO_PATH", "images/logo.png")


@dataclass(frozen=True)
class ContactSettings:
    email: str = env_value("STORE_EMAIL", "contato@vjsemijoias.com")
    phone: str = env_value("STORE_PHONE", "(51) 98211-0842")
    whatsapp: str = env_value("STORE_WHATSAPP", "51 982110842")
    instagram: str = env_value("STORE_INSTAGRAM", "vj_semijoias")
    website: str = env_value("STORE_WEBSITE", "www.vjsemijoias.com")
    cnpj: str = env_value("STORE_CNPJ", "")


@dataclass(frozen=True)
class CatalogSettings:
    title: str = env_value("STORE_CATALOG_TITLE", "CATALOGO VJ SEMIJOIAS")
    collection: str = env_value(
        "STORE_CATALOG_COLLECTION",
        "Colecao Banhada a Ouro 18k",
    )
    filename: str = env_value("STORE_CATALOG_FILENAME", "catalogo-vj-semijoias.pdf")


@dataclass(frozen=True)
class ShippingSettings:
    mode: str = env_value("SHIPPING_MODE", "free").lower()
    fixed_value: str = env_value("SHIPPING_FIXED_VALUE", "0")
    free_minimum: str = env_value("SHIPPING_FREE_MINIMUM", "0")
    estimated_days: str = env_value("SHIPPING_ESTIMATED_DAYS", "5-10")
    provider: str = env_value("SHIPPING_PROVIDER", "internal").lower()
    melhor_envio_from_postal_code: str = env_value("MELHOR_ENVIO_FROM_POSTAL_CODE", "")
    melhor_envio_services: str = env_value("MELHOR_ENVIO_SERVICES", "")
    melhor_envio_allowed_company_ids: str = env_value("MELHOR_ENVIO_ALLOWED_COMPANY_IDS", "1,2,14,15,12,6")
    melhor_envio_timeout_seconds: str = env_value("MELHOR_ENVIO_TIMEOUT_SECONDS", "6")


@dataclass(frozen=True)
class CouponSettings:
    enabled: bool = env_bool("COUPONS_ENABLED", True)
    code: str = env_value("COUPON_CODE", "VJ10").upper()
    discount_percent: str = env_value("COUPON_DISCOUNT_PERCENT", "10")
    usage_limit: int = env_int("COUPON_USAGE_LIMIT", 100)


@dataclass(frozen=True)
class StoreSettings:
    brand: BrandSettings = BrandSettings()
    contact: ContactSettings = ContactSettings()
    catalog: CatalogSettings = CatalogSettings()
    shipping: ShippingSettings = ShippingSettings()
    coupon: CouponSettings = CouponSettings()

    @property
    def logo_file(self):
        return FRONTEND_ROOT / self.brand.logo_path

    @property
    def catalog_contact_line(self):
        parts = []
        if self.contact.website:
            parts.append(self.contact.website)
        if self.contact.instagram:
            parts.append(f"Instagram: @{self.contact.instagram.lstrip('@')}")
        if self.contact.whatsapp:
            parts.append(f"WhatsApp: {self.contact.whatsapp}")
        return " | ".join(parts)

    @property
    def coupon_label(self):
        if not self.coupon.enabled or not self.coupon.code:
            return ""
        return f"{self.coupon.code} = {self.coupon.discount_percent}% OFF"

    def public_dict(self):
        return {
            "brand": asdict(self.brand),
            "contact": asdict(self.contact),
            "catalog": {
                **asdict(self.catalog),
                "contact_line": self.catalog_contact_line,
                "coupon_label": self.coupon_label,
            },
            "shipping": {
                "mode": self.shipping.mode,
                "fixed_value": self.shipping.fixed_value,
                "free_minimum": self.shipping.free_minimum,
                "estimated_days": self.shipping.estimated_days,
            },
            "coupon": {
                "enabled": self.coupon.enabled,
                "code": self.coupon.code if self.coupon.enabled else "",
                "discount_percent": self.coupon.discount_percent
                if self.coupon.enabled
                else "0",
                "usage_limit": self.coupon.usage_limit,
            },
        }


store_settings = StoreSettings()


STORE_SETTING_KEYS = (
    "STORE_NAME",
    "STORE_SHORT_NAME",
    "STORE_TAGLINE",
    "STORE_DESCRIPTION",
    "STORE_SLOGAN",
    "STORE_LOGO_PATH",
    "STORE_EMAIL",
    "STORE_PHONE",
    "STORE_WHATSAPP",
    "STORE_INSTAGRAM",
    "STORE_WEBSITE",
    "STORE_CNPJ",
    "STORE_CATALOG_TITLE",
    "STORE_CATALOG_COLLECTION",
    "STORE_CATALOG_FILENAME",
    "SHIPPING_MODE",
    "SHIPPING_FIXED_VALUE",
    "SHIPPING_FREE_MINIMUM",
    "SHIPPING_ESTIMATED_DAYS",
    "SHIPPING_PROVIDER",
    "MELHOR_ENVIO_FROM_POSTAL_CODE",
    "MELHOR_ENVIO_SERVICES",
    "MELHOR_ENVIO_ALLOWED_COMPANY_IDS",
    "MELHOR_ENVIO_TIMEOUT_SECONDS",
    "COUPONS_ENABLED",
    "COUPON_CODE",
    "COUPON_DISCOUNT_PERCENT",
    "COUPON_USAGE_LIMIT",
    "EMAIL_BACKEND",
    "EMAIL_FROM_NAME",
    "EMAIL_FROM_ADDRESS",
    "EMAIL_SMTP_HOST",
    "EMAIL_SMTP_PORT",
    "EMAIL_SMTP_USERNAME",
    "EMAIL_SMTP_PASSWORD",
    "EMAIL_SMTP_USE_TLS",
)


def default_store_values(settings_obj: StoreSettings = store_settings):
    return {
        "STORE_NAME": settings_obj.brand.name,
        "STORE_SHORT_NAME": settings_obj.brand.short_name,
        "STORE_TAGLINE": settings_obj.brand.tagline,
        "STORE_DESCRIPTION": settings_obj.brand.description,
        "STORE_SLOGAN": settings_obj.brand.slogan,
        "STORE_LOGO_PATH": settings_obj.brand.logo_path,
        "STORE_EMAIL": settings_obj.contact.email,
        "STORE_PHONE": settings_obj.contact.phone,
        "STORE_WHATSAPP": settings_obj.contact.whatsapp,
        "STORE_INSTAGRAM": settings_obj.contact.instagram,
        "STORE_WEBSITE": settings_obj.contact.website,
        "STORE_CNPJ": settings_obj.contact.cnpj,
        "STORE_CATALOG_TITLE": settings_obj.catalog.title,
        "STORE_CATALOG_COLLECTION": settings_obj.catalog.collection,
        "STORE_CATALOG_FILENAME": settings_obj.catalog.filename,
        "SHIPPING_MODE": settings_obj.shipping.mode,
        "SHIPPING_FIXED_VALUE": settings_obj.shipping.fixed_value,
        "SHIPPING_FREE_MINIMUM": settings_obj.shipping.free_minimum,
        "SHIPPING_ESTIMATED_DAYS": settings_obj.shipping.estimated_days,
        "SHIPPING_PROVIDER": settings_obj.shipping.provider,
        "MELHOR_ENVIO_FROM_POSTAL_CODE": settings_obj.shipping.melhor_envio_from_postal_code,
        "MELHOR_ENVIO_SERVICES": settings_obj.shipping.melhor_envio_services,
        "MELHOR_ENVIO_ALLOWED_COMPANY_IDS": settings_obj.shipping.melhor_envio_allowed_company_ids,
        "MELHOR_ENVIO_TIMEOUT_SECONDS": settings_obj.shipping.melhor_envio_timeout_seconds,
        "COUPONS_ENABLED": bool_text(settings_obj.coupon.enabled),
        "COUPON_CODE": settings_obj.coupon.code,
        "COUPON_DISCOUNT_PERCENT": settings_obj.coupon.discount_percent,
        "COUPON_USAGE_LIMIT": str(settings_obj.coupon.usage_limit),
        "EMAIL_BACKEND": settings.email_backend,
        "EMAIL_FROM_NAME": settings.email_from_name,
        "EMAIL_FROM_ADDRESS": settings.email_from_address,
        "EMAIL_SMTP_HOST": settings.email_smtp_host,
        "EMAIL_SMTP_PORT": str(settings.email_smtp_port),
        "EMAIL_SMTP_USERNAME": settings.email_smtp_username,
        "EMAIL_SMTP_PASSWORD": settings.email_smtp_password,
        "EMAIL_SMTP_USE_TLS": bool_text(settings.email_smtp_use_tls),
    }


def load_store_overrides(db: Session | None):
    if db is None:
        return {}
    rows = db.scalars(select(StoreSetting)).all()
    return {row.key: row.value for row in rows if row.key in STORE_SETTING_KEYS}


def normalize_csv_ints(value, *, field: str) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        return ""
    parts = [part.strip() for part in raw_value.split(",") if part.strip()]
    if not parts or any(not part.isdigit() for part in parts):
        raise ValueError(f"{field} deve conter apenas numeros separados por virgula")
    return ",".join(parts)


def normalize_timeout_seconds(value) -> str:
    try:
        timeout = Decimal(str(value or "6")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("MELHOR_ENVIO_TIMEOUT_SECONDS deve ser numerico") from exc
    if timeout < Decimal("1") or timeout > Decimal("30"):
        raise ValueError("MELHOR_ENVIO_TIMEOUT_SECONDS deve ficar entre 1 e 30")
    return format(timeout.normalize(), "f")

def validate_store_values(values):
    cleaned = {}
    defaults = default_store_values()
    for key, value in values.items():
        if key not in STORE_SETTING_KEYS:
            continue
        cleaned[key] = str(value if value is not None else "").strip()

    if "SHIPPING_MODE" in cleaned:
        cleaned["SHIPPING_MODE"] = cleaned["SHIPPING_MODE"].lower()
        if cleaned["SHIPPING_MODE"] not in {"free", "fixed", "threshold"}:
            raise ValueError("SHIPPING_MODE deve ser free, fixed ou threshold")

    if "EMAIL_BACKEND" in cleaned:
        cleaned["EMAIL_BACKEND"] = cleaned["EMAIL_BACKEND"].lower()
        if cleaned["EMAIL_BACKEND"] not in {"console", "smtp", "disabled"}:
            raise ValueError("EMAIL_BACKEND deve ser console, smtp ou disabled")

    if "SHIPPING_PROVIDER" in cleaned:
        cleaned["SHIPPING_PROVIDER"] = cleaned["SHIPPING_PROVIDER"].lower()
        if cleaned["SHIPPING_PROVIDER"] not in {"internal", "melhor_envio"}:
            raise ValueError("SHIPPING_PROVIDER deve ser internal ou melhor_envio")

    if "MELHOR_ENVIO_FROM_POSTAL_CODE" in cleaned:
        postal_code = digits_only(cleaned["MELHOR_ENVIO_FROM_POSTAL_CODE"])
        if cleaned["MELHOR_ENVIO_FROM_POSTAL_CODE"] and len(postal_code) != 8:
            raise ValueError("MELHOR_ENVIO_FROM_POSTAL_CODE deve conter 8 digitos")
        cleaned["MELHOR_ENVIO_FROM_POSTAL_CODE"] = postal_code

    for key in ("MELHOR_ENVIO_SERVICES", "MELHOR_ENVIO_ALLOWED_COMPANY_IDS"):
        if key in cleaned:
            cleaned[key] = normalize_csv_ints(cleaned[key], field=key)

    if "MELHOR_ENVIO_TIMEOUT_SECONDS" in cleaned:
        cleaned["MELHOR_ENVIO_TIMEOUT_SECONDS"] = normalize_timeout_seconds(cleaned["MELHOR_ENVIO_TIMEOUT_SECONDS"])

    if "EMAIL_SMTP_PORT" in cleaned:
        try:
            smtp_port = int(cleaned["EMAIL_SMTP_PORT"] or "587")
        except ValueError as exc:
            raise ValueError("EMAIL_SMTP_PORT deve ser um numero inteiro") from exc
        if smtp_port < 1 or smtp_port > 65535:
            raise ValueError("EMAIL_SMTP_PORT deve ficar entre 1 e 65535")
        cleaned["EMAIL_SMTP_PORT"] = str(smtp_port)

    for key in ("SHIPPING_FIXED_VALUE", "SHIPPING_FREE_MINIMUM", "COUPON_DISCOUNT_PERCENT"):
        if key in cleaned:
            cleaned[key] = str(money_value(cleaned[key]))

    shipping_mode = cleaned.get("SHIPPING_MODE", defaults["SHIPPING_MODE"])
    shipping_provider = cleaned.get("SHIPPING_PROVIDER", defaults["SHIPPING_PROVIDER"])
    shipping_fixed_value = money_value(cleaned.get("SHIPPING_FIXED_VALUE", defaults["SHIPPING_FIXED_VALUE"]))
    shipping_free_minimum = money_value(cleaned.get("SHIPPING_FREE_MINIMUM", defaults["SHIPPING_FREE_MINIMUM"]))
    if shipping_mode == "threshold" and shipping_free_minimum <= 0:
        raise ValueError("SHIPPING_FREE_MINIMUM deve ser maior que zero no modo threshold")
    if shipping_mode == "threshold" and shipping_provider == "internal" and shipping_fixed_value <= 0:
        raise ValueError("SHIPPING_FIXED_VALUE deve ser maior que zero para frete gratis acima de um valor")

    if "COUPON_DISCOUNT_PERCENT" in cleaned:
        percent = money_value(cleaned["COUPON_DISCOUNT_PERCENT"])
        if percent < 0 or percent > 100:
            raise ValueError("COUPON_DISCOUNT_PERCENT deve ficar entre 0 e 100")

    if "COUPON_USAGE_LIMIT" in cleaned:
        try:
            usage_limit = int(cleaned["COUPON_USAGE_LIMIT"])
        except ValueError as exc:
            raise ValueError("COUPON_USAGE_LIMIT deve ser um numero inteiro") from exc
        if usage_limit < 0:
            raise ValueError("COUPON_USAGE_LIMIT nao pode ser negativo")
        cleaned["COUPON_USAGE_LIMIT"] = str(usage_limit)

    if "EMAIL_SMTP_USE_TLS" in cleaned:
        cleaned["EMAIL_SMTP_USE_TLS"] = bool_text(parse_bool(cleaned["EMAIL_SMTP_USE_TLS"]))

    if "COUPONS_ENABLED" in cleaned:
        cleaned["COUPONS_ENABLED"] = bool_text(parse_bool(cleaned["COUPONS_ENABLED"]))

    if "COUPON_CODE" in cleaned:
        cleaned["COUPON_CODE"] = cleaned["COUPON_CODE"].upper()

    text_limits = {
        "STORE_NAME": 120,
        "STORE_SHORT_NAME": 30,
        "STORE_TAGLINE": 80,
        "STORE_DESCRIPTION": 500,
        "STORE_SLOGAN": 120,
        "STORE_LOGO_PATH": 200,
        "STORE_INSTAGRAM": 80,
        "STORE_WEBSITE": 200,
        "STORE_CNPJ": 30,
        "STORE_CATALOG_TITLE": 120,
        "STORE_CATALOG_COLLECTION": 120,
        "STORE_CATALOG_FILENAME": 120,
        "SHIPPING_ESTIMATED_DAYS": 30,
        "SHIPPING_PROVIDER": 30,
        "MELHOR_ENVIO_FROM_POSTAL_CODE": 20,
        "MELHOR_ENVIO_SERVICES": 100,
        "MELHOR_ENVIO_ALLOWED_COMPANY_IDS": 100,
        "MELHOR_ENVIO_TIMEOUT_SECONDS": 10,
        "COUPON_CODE": 30,
        "EMAIL_BACKEND": 30,
        "EMAIL_FROM_NAME": 120,
        "EMAIL_SMTP_HOST": 200,
        "EMAIL_SMTP_USERNAME": 200,
        "EMAIL_SMTP_PASSWORD": 300,
    }
    for key, max_length in text_limits.items():
        if key in cleaned:
            cleaned[key] = clean_text(cleaned[key], field=key, max_length=max_length)

    if "EMAIL_FROM_ADDRESS" in cleaned and cleaned["EMAIL_FROM_ADDRESS"]:
        cleaned["EMAIL_FROM_ADDRESS"] = normalize_email(cleaned["EMAIL_FROM_ADDRESS"])
    if "STORE_EMAIL" in cleaned and cleaned["STORE_EMAIL"]:
        cleaned["STORE_EMAIL"] = normalize_email(cleaned["STORE_EMAIL"])
    if "STORE_PHONE" in cleaned and cleaned["STORE_PHONE"]:
        cleaned["STORE_PHONE"] = normalize_phone(cleaned["STORE_PHONE"])
    if "STORE_WHATSAPP" in cleaned and cleaned["STORE_WHATSAPP"]:
        cleaned["STORE_WHATSAPP"] = normalize_phone(cleaned["STORE_WHATSAPP"])

    return {key: cleaned.get(key, defaults[key]) for key in STORE_SETTING_KEYS}


def settings_from_values(values):
    data = {**default_store_values(), **values}
    return StoreSettings(
        brand=BrandSettings(
            name=data["STORE_NAME"],
            short_name=data["STORE_SHORT_NAME"],
            tagline=data["STORE_TAGLINE"],
            description=data["STORE_DESCRIPTION"],
            slogan=data["STORE_SLOGAN"],
            logo_path=data["STORE_LOGO_PATH"],
        ),
        contact=ContactSettings(
            email=data["STORE_EMAIL"],
            phone=data["STORE_PHONE"],
            whatsapp=data["STORE_WHATSAPP"],
            instagram=data["STORE_INSTAGRAM"],
            website=data["STORE_WEBSITE"],
            cnpj=data["STORE_CNPJ"],
        ),
        catalog=CatalogSettings(
            title=data["STORE_CATALOG_TITLE"],
            collection=data["STORE_CATALOG_COLLECTION"],
            filename=data["STORE_CATALOG_FILENAME"],
        ),
        shipping=ShippingSettings(
            mode=data["SHIPPING_MODE"].lower(),
            fixed_value=data["SHIPPING_FIXED_VALUE"],
            free_minimum=data["SHIPPING_FREE_MINIMUM"],
            estimated_days=data["SHIPPING_ESTIMATED_DAYS"],
            provider=data["SHIPPING_PROVIDER"].lower(),
            melhor_envio_from_postal_code=data["MELHOR_ENVIO_FROM_POSTAL_CODE"],
            melhor_envio_services=data["MELHOR_ENVIO_SERVICES"],
            melhor_envio_allowed_company_ids=data["MELHOR_ENVIO_ALLOWED_COMPANY_IDS"],
            melhor_envio_timeout_seconds=data["MELHOR_ENVIO_TIMEOUT_SECONDS"],
        ),
        coupon=CouponSettings(
            enabled=parse_bool(data["COUPONS_ENABLED"]),
            code=data["COUPON_CODE"].upper(),
            discount_percent=data["COUPON_DISCOUNT_PERCENT"],
            usage_limit=int(data["COUPON_USAGE_LIMIT"] or "0"),
        ),
    )


def effective_store_settings(db: Session | None = None):
    return settings_from_values(load_store_overrides(db))


def public_store_config(db: Session | None = None):
    active_settings = effective_store_settings(db)
    data = active_settings.public_dict()
    data["shipping"].update(
        {
            "fixed_value": float(money_value(active_settings.shipping.fixed_value)),
            "free_minimum": float(money_value(active_settings.shipping.free_minimum)),
        }
    )
    data["coupon"]["discount_percent"] = (
        float(money_value(active_settings.coupon.discount_percent))
        if active_settings.coupon.enabled
        else 0
    )
    return data


def mask_sensitive_admin_values(values):
    masked = dict(values)
    masked["EMAIL_SMTP_PASSWORD"] = ""
    return masked


def admin_store_config(db: Session):
    values = {**default_store_values(), **load_store_overrides(db)}
    return {
        "values": mask_sensitive_admin_values(values),
        "defaults": mask_sensitive_admin_values(default_store_values()),
        "public": public_store_config(db),
    }


def sync_coupon_record(db: Session, active_settings: StoreSettings):
    if not active_settings.coupon.code:
        return
    coupon = db.scalar(select(Coupon).where(Coupon.code == active_settings.coupon.code))
    if not coupon:
        coupon = Coupon(code=active_settings.coupon.code)
        db.add(coupon)
    coupon.discount_percent = money_value(active_settings.coupon.discount_percent)
    coupon.discount_type = "percent"
    coupon.discount_value = money_value(active_settings.coupon.discount_percent)
    coupon.usage_limit = active_settings.coupon.usage_limit
    coupon.is_active = active_settings.coupon.enabled


def update_store_settings(db: Session, values):
    current_values = {**default_store_values(), **load_store_overrides(db)}
    incoming_values = dict(values or {})
    if not str(incoming_values.get("EMAIL_SMTP_PASSWORD", "")).strip():
        incoming_values.pop("EMAIL_SMTP_PASSWORD", None)
    cleaned = validate_store_values({**current_values, **incoming_values})
    for key, value in cleaned.items():
        row = db.get(StoreSetting, key)
        if row:
            row.value = value
        else:
            db.add(StoreSetting(key=key, value=value))
    active_settings = settings_from_values(cleaned)
    sync_coupon_record(db, active_settings)
    db.commit()
    return admin_store_config(db)
