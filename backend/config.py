import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
IMPORT_UPLOAD_ROOT = PROJECT_ROOT / "import_data" / "uploads"
INSTANCE_ROOT = PROJECT_ROOT / "instance"

load_dotenv(Path(__file__).with_name(".env"))
load_dotenv(PROJECT_ROOT / ".env")


def env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def database_url():
    value = os.getenv("DATABASE_URL", "sqlite:///vjsemijoias.db")
    if value == "sqlite://":
        return value
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    if value.startswith("sqlite:///") and not value.startswith("sqlite:////"):
        path = Path(value.removeprefix("sqlite:///"))
        if not path.is_absolute():
            INSTANCE_ROOT.mkdir(parents=True, exist_ok=True)
            path = INSTANCE_ROOT / path
        return f"sqlite:///{path.as_posix()}"
    return value


@dataclass(frozen=True)
class Settings:
    database_url: str = database_url()
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "jwt-secret-key")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    infinitepay_handle: str = os.getenv("INFINITEPAY_HANDLE", "").strip().lstrip("$")
    infinitepay_api_base: str = os.getenv(
        "INFINITEPAY_API_BASE",
        "https://api.checkout.infinitepay.io",
    )
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    port: int = int(os.getenv("PORT", "5000"))
    debug: bool = env_bool("DEBUG", False)

    @property
    def shipping_mode(self):
        from backend.store_config import store_settings

        return store_settings.shipping.mode

    @property
    def shipping_fixed_value(self):
        from backend.store_config import store_settings

        return store_settings.shipping.fixed_value

    @property
    def shipping_free_minimum(self):
        from backend.store_config import store_settings

        return store_settings.shipping.free_minimum

    @property
    def shipping_estimated_days(self):
        from backend.store_config import store_settings

        return store_settings.shipping.estimated_days

    @property
    def coupons_enabled(self):
        from backend.store_config import store_settings

        return store_settings.coupon.enabled

    @property
    def coupon_code(self):
        from backend.store_config import store_settings

        return store_settings.coupon.code

    @property
    def coupon_discount_percent(self):
        from backend.store_config import store_settings

        return store_settings.coupon.discount_percent

    @property
    def coupon_usage_limit(self):
        from backend.store_config import store_settings

        return store_settings.coupon.usage_limit


settings = Settings()
