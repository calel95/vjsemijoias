import secrets

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from backend.config import settings


SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
CSRF_EXEMPT_PATHS = {
    "/api/auth/login",
    "/api/auth/register",
    "/api/auth/admin/login",
}


def create_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def set_csrf_cookie(response: Response, token: str | None = None) -> str:
    csrf_token = token or create_csrf_token()
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=max(settings.user_token_expire_days * 24 * 60 * 60, 1),
        httponly=False,
        secure=settings.csrf_cookie_secure,
        samesite=settings.csrf_cookie_samesite,
        path="/",
    )
    return csrf_token


def delete_csrf_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.csrf_cookie_name,
        path="/",
        secure=settings.csrf_cookie_secure,
        httponly=False,
        samesite=settings.csrf_cookie_samesite,
    )


def uses_cookie_auth(request: Request) -> bool:
    if request.headers.get("authorization"):
        return False
    return bool(
        request.cookies.get(settings.admin_cookie_name)
        or request.cookies.get(settings.user_cookie_name)
    )


async def csrf_middleware(request: Request, call_next):
    if (
        request.method in SAFE_METHODS
        or request.url.path in CSRF_EXEMPT_PATHS
        or not request.url.path.startswith("/api/")
        or not uses_cookie_auth(request)
    ):
        return await call_next(request)

    cookie_token = request.cookies.get(settings.csrf_cookie_name)
    header_token = request.headers.get(settings.csrf_header_name)
    if (
        not cookie_token
        or not header_token
        or not secrets.compare_digest(cookie_token, header_token)
    ):
        return JSONResponse(
            status_code=403,
            content={"error": "Token CSRF ausente ou invalido"},
        )

    return await call_next(request)
