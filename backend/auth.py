from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import settings


bearer = HTTPBearer(auto_error=False)


def create_access_token(user):
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user.id),
            "is_admin": user.is_admin,
            "name": user.name,
            "email": user.email,
            "iat": now,
            "exp": now + timedelta(days=7),
        },
        settings.jwt_secret_key,
        algorithm="HS256",
    )


def decode_token(credentials: HTTPAuthorizationCredentials | None):
    if credentials is None:
        return None
    try:
        return jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=["HS256"],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado") from exc


def optional_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    return decode_token(credentials)


def required_claims(claims=Depends(optional_claims)):
    if claims is None:
        raise HTTPException(status_code=401, detail="Autenticação necessária")
    return claims


def admin_claims(claims=Depends(required_claims)):
    if not claims.get("is_admin"):
        raise HTTPException(
            status_code=403,
            detail="Acesso restrito a administradores",
        )
    return claims
