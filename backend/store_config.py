import os
from dataclasses import asdict, dataclass

from backend.config import FRONTEND_ROOT, env_bool


def env_value(name, default=""):
    return os.getenv(name, default).strip()


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
    usage_limit: int = int(env_value("COUPON_USAGE_LIMIT", "100") or "100")


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
