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


def env_list(name):
    value = os.getenv(name, "")
    return [item.strip().rstrip("/") for item in value.split(",") if item.strip()]


def cors_allowed_origins():
    origins = env_list("CORS_ALLOWED_ORIGINS")
    public_base_url = os.getenv("PUBLIC_BASE_URL", "").strip().rstrip("/")
    if public_base_url and public_base_url not in origins:
        origins.append(public_base_url)
    if origins:
        return origins
    return [
        "http://localhost:5000",
        "http://127.0.0.1:5000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]


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
    admin_token_expire_minutes: int = int(os.getenv("ADMIN_TOKEN_EXPIRE_MINUTES", "120"))
    admin_login_max_attempts: int = int(os.getenv("ADMIN_LOGIN_MAX_ATTEMPTS", "5"))
    admin_login_lockout_seconds: int = int(os.getenv("ADMIN_LOGIN_LOCKOUT_SECONDS", "300"))
    admin_cookie_name: str = os.getenv("ADMIN_COOKIE_NAME", "vj_admin_token")
    admin_cookie_secure: bool = env_bool(
        "ADMIN_COOKIE_SECURE",
        os.getenv("PUBLIC_BASE_URL", "").strip().startswith("https://"),
    )
    admin_cookie_samesite: str = os.getenv("ADMIN_COOKIE_SAMESITE", "lax").strip().lower()
    user_token_expire_days: int = int(os.getenv("USER_TOKEN_EXPIRE_DAYS", "7"))
    user_cookie_name: str = os.getenv("USER_COOKIE_NAME", "vj_user_token")
    user_cookie_secure: bool = env_bool(
        "USER_COOKIE_SECURE",
        os.getenv("PUBLIC_BASE_URL", "").strip().startswith("https://"),
    )
    user_cookie_samesite: str = os.getenv("USER_COOKIE_SAMESITE", "lax").strip().lower()
    infinitepay_handle: str = os.getenv("INFINITEPAY_HANDLE", "").strip().lstrip("$")
    infinitepay_api_base: str = os.getenv(
        "INFINITEPAY_API_BASE",
        "https://api.checkout.infinitepay.io",
    )
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    cors_allowed_origins: tuple[str, ...] = tuple(cors_allowed_origins())
    port: int = int(os.getenv("PORT", "5000"))
    debug: bool = env_bool("DEBUG", False)
    rate_limit_enabled: bool = env_bool("RATE_LIMIT_ENABLED", True)
    rate_limit_global_per_minute: int = int(os.getenv("RATE_LIMIT_GLOBAL_PER_MINUTE", "300"))
    rate_limit_public_per_minute: int = int(os.getenv("RATE_LIMIT_PUBLIC_PER_MINUTE", "180"))
    rate_limit_auth_per_minute: int = int(os.getenv("RATE_LIMIT_AUTH_PER_MINUTE", "20"))
    rate_limit_write_per_minute: int = int(os.getenv("RATE_LIMIT_WRITE_PER_MINUTE", "60"))
    rate_limit_expensive_per_minute: int = int(os.getenv("RATE_LIMIT_EXPENSIVE_PER_MINUTE", "5"))

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
