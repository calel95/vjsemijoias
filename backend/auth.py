from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Cookie, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.models import User


bearer = HTTPBearer(auto_error=False)


def create_access_token(user, *, expires_delta: timedelta | None = None, token_use="user"):
    now = datetime.now(UTC)
    expires_at = now + (expires_delta or timedelta(days=7))
    return jwt.encode(
        {
            "sub": str(user.id),
            "is_admin": user.is_admin,
            "name": user.name,
            "email": user.email,
            "token_use": token_use,
            "iat": now,
            "exp": expires_at,
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )


def create_admin_access_token(user):
    return create_access_token(
        user,
        expires_delta=timedelta(minutes=settings.admin_token_expire_minutes),
        token_use="admin",
    )


def decode_token_value(token: str | None):
    if not token:
        return None
    try:
        return jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado") from exc


def decode_token(credentials: HTTPAuthorizationCredentials | None):
    return decode_token_value(credentials.credentials if credentials else None)


def optional_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    admin_cookie: str | None = Cookie(default=None, alias=settings.admin_cookie_name),
):
    if credentials is not None:
        return decode_token(credentials)
    return decode_token_value(admin_cookie)


def required_claims(claims=Depends(optional_claims)):
    if claims is None:
        raise HTTPException(status_code=401, detail="Autenticação necessária")
    return claims


def admin_claims(
    claims=Depends(required_claims),
    db: Session = Depends(get_db),
):
    if claims.get("token_use") != "admin":
        raise HTTPException(
            status_code=403,
            detail="SessÃ£o administrativa necessÃ¡ria",
        )
    try:
        user_id = int(claims["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Token invÃ¡lido") from exc

    user = db.get(User, user_id)
    if not user or not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Acesso restrito a administradores",
        )
    return claims
