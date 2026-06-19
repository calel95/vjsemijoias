import time
from dataclasses import dataclass

from fastapi import Request
from fastapi.responses import JSONResponse

from backend.config import settings


RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_STATE: dict[tuple[str, str], tuple[int, float]] = {}
RATE_LIMIT_EXEMPT_PATHS = {"/api/health", "/api/ready"}
EXPENSIVE_PATHS = {
    "/api/products/import-folder",
    "/api/admin/catalog-pdf",
}
AUTH_PATHS = {
    "/api/auth/admin/login",
    "/api/auth/login",
    "/api/auth/register",
}


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    limit: int


def rate_limit_client_key(request: Request):
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    return request.client.host if request.client else "unknown"


def rate_limit_rules(request: Request):
    path = request.url.path
    method = request.method.upper()
    rules = [RateLimitRule("global", settings.rate_limit_global_per_minute)]

    if path in AUTH_PATHS:
        rules.append(RateLimitRule("auth", settings.rate_limit_auth_per_minute))
    elif path in EXPENSIVE_PATHS:
        rules.append(RateLimitRule("expensive", settings.rate_limit_expensive_per_minute))
    elif method in {"POST", "PUT", "PATCH", "DELETE"}:
        rules.append(RateLimitRule("write", settings.rate_limit_write_per_minute))
    else:
        rules.append(RateLimitRule("public", settings.rate_limit_public_per_minute))

    return [rule for rule in rules if rule.limit > 0]


def check_rate_limit(request: Request):
    if not settings.rate_limit_enabled:
        return None
    if request.method.upper() == "OPTIONS":
        return None
    if not request.url.path.startswith("/api/"):
        return None
    if request.url.path in RATE_LIMIT_EXEMPT_PATHS:
        return None

    now = time.time()
    client_key = rate_limit_client_key(request)
    response_headers = {}

    for rule in rate_limit_rules(request):
        key = (client_key, rule.name)
        count, reset_at = RATE_LIMIT_STATE.get(key, (0, now + RATE_LIMIT_WINDOW_SECONDS))
        if now >= reset_at:
            count = 0
            reset_at = now + RATE_LIMIT_WINDOW_SECONDS

        if count >= rule.limit:
            retry_after = max(1, int(reset_at - now))
            return JSONResponse(
                status_code=429,
                content={"error": "Muitas requisicoes. Tente novamente em instantes."},
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(rule.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_at)),
                },
            )

        count += 1
        RATE_LIMIT_STATE[key] = (count, reset_at)
        if rule.name != "global":
            response_headers = {
                "X-RateLimit-Limit": str(rule.limit),
                "X-RateLimit-Remaining": str(max(rule.limit - count, 0)),
                "X-RateLimit-Reset": str(int(reset_at)),
            }

    return response_headers


async def rate_limit_middleware(request: Request, call_next):
    result = check_rate_limit(request)
    if isinstance(result, JSONResponse):
        return result

    response = await call_next(request)
    for name, value in (result or {}).items():
        response.headers[name] = value
    return response


def clear_rate_limit_state():
    RATE_LIMIT_STATE.clear()
