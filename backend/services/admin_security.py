import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import AdminAuditLog, User


ADMIN_LOGIN_ATTEMPTS: dict[str, dict[str, Any]] = {}


def admin_login_key(request: Request):
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    return request.client.host if request.client else "unknown"


def check_admin_login_rate_limit(request: Request):
    state = ADMIN_LOGIN_ATTEMPTS.get(admin_login_key(request))
    if not state:
        return
    locked_until = state.get("locked_until")
    if locked_until and datetime.now(UTC) < locked_until:
        raise HTTPException(
            status_code=429,
            detail="Muitas tentativas incorretas. Tente novamente em alguns minutos.",
        )


def record_admin_login_failure(request: Request):
    max_attempts = max(settings.admin_login_max_attempts, 1)
    state = ADMIN_LOGIN_ATTEMPTS.setdefault(
        admin_login_key(request),
        {"attempts": 0, "locked_until": None},
    )
    state["attempts"] += 1
    if state["attempts"] >= max_attempts:
        state["locked_until"] = datetime.now(UTC) + timedelta(
            seconds=max(settings.admin_login_lockout_seconds, 1)
        )


def clear_admin_login_failures(request: Request):
    ADMIN_LOGIN_ATTEMPTS.pop(admin_login_key(request), None)


def record_admin_audit(
    db: Session,
    request: Request,
    action: str,
    *,
    admin_user: User | None = None,
    resource: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
):
    db.add(
        AdminAuditLog(
            admin_user_id=admin_user.id if admin_user else None,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip_address=admin_login_key(request),
            user_agent=request.headers.get("user-agent"),
            metadata_json=json.dumps(metadata or {}, ensure_ascii=False),
        )
    )
