import os
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import FRONTEND_ROOT, env_bool
from backend.models import Coupon, StoreSetting


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
            "shipping": asdict(self.shipping),
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
    "COUPONS_ENABLED",
    "COUPON_CODE",
    "COUPON_DISCOUNT_PERCENT",
    "COUPON_USAGE_LIMIT",
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
        "COUPONS_ENABLED": bool_text(settings_obj.coupon.enabled),
        "COUPON_CODE": settings_obj.coupon.code,
        "COUPON_DISCOUNT_PERCENT": settings_obj.coupon.discount_percent,
        "COUPON_USAGE_LIMIT": str(settings_obj.coupon.usage_limit),
    }


def load_store_overrides(db: Session | None):
    if db is None:
        return {}
    rows = db.scalars(select(StoreSetting)).all()
    return {row.key: row.value for row in rows if row.key in STORE_SETTING_KEYS}


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

    for key in ("SHIPPING_FIXED_VALUE", "SHIPPING_FREE_MINIMUM", "COUPON_DISCOUNT_PERCENT"):
        if key in cleaned:
            cleaned[key] = str(money_value(cleaned[key]))

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

    if "COUPONS_ENABLED" in cleaned:
        cleaned["COUPONS_ENABLED"] = bool_text(parse_bool(cleaned["COUPONS_ENABLED"]))

    if "COUPON_CODE" in cleaned:
        cleaned["COUPON_CODE"] = cleaned["COUPON_CODE"].upper()

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


def admin_store_config(db: Session):
    values = {**default_store_values(), **load_store_overrides(db)}
    return {
        "values": values,
        "defaults": default_store_values(),
        "public": public_store_config(db),
    }


def sync_coupon_record(db: Session, active_settings: StoreSettings):
    if not active_settings.coupon.code:
        return
    db.query(Coupon).where(Coupon.code != active_settings.coupon.code).update(
        {Coupon.is_active: False},
        synchronize_session=False,
    )
    coupon = db.scalar(select(Coupon).where(Coupon.code == active_settings.coupon.code))
    if not coupon:
        coupon = Coupon(code=active_settings.coupon.code)
        db.add(coupon)
    coupon.discount_percent = float(money_value(active_settings.coupon.discount_percent))
    coupon.usage_limit = active_settings.coupon.usage_limit
    coupon.is_active = active_settings.coupon.enabled


def update_store_settings(db: Session, values):
    current_values = {**default_store_values(), **load_store_overrides(db)}
    cleaned = validate_store_values({**current_values, **(values or {})})
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
