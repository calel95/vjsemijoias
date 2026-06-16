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
    debug: bool = os.getenv("DEBUG", "").lower() in {
        "1",
        "true",
        "yes",
    }


settings = Settings()
