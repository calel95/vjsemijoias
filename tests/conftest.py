import os

import pytest


os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ADMIN_PASSWORD"] = "test-admin-password"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-with-at-least-32-bytes"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["INFINITEPAY_HANDLE"] = "vjsemijoias"
os.environ["PUBLIC_BASE_URL"] = "https://vj.example.com"
os.environ["CORS_ALLOWED_ORIGINS"] = "https://vj.example.com,http://localhost:5000"
os.environ["STORAGE_BACKEND"] = "local"

from backend.database import Base, engine  # noqa: E402
import backend.models  # noqa: E402,F401


Base.metadata.create_all(engine)

from backend.app import app as _app  # noqa: E402,F401
from backend.services.rate_limit import clear_rate_limit_state  # noqa: E402


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    clear_rate_limit_state()
    yield
    clear_rate_limit_state()
