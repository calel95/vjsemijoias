from __future__ import annotations

import json
from typing import Any

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.models import AdminAuditLog
from backend.services.vj_finance import datetime_after, datetime_start, parse_date


def request_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        return forwarded_for
    return request.client.host if request.client else "unknown"


def compact_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    allowed = {}
    for key, value in (metadata or {}).items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            allowed[key] = value
        elif isinstance(value, list):
            allowed[key] = [item for item in value if isinstance(item, (str, int, float, bool, type(None)))]
        elif isinstance(value, dict):
            allowed[key] = {
                str(sub_key): sub_value
                for sub_key, sub_value in value.items()
                if isinstance(sub_value, (str, int, float, bool, type(None)))
            }
    return allowed


def record_vj_admin_audit(
    db: Session,
    request: Request,
    *,
    admin_user_id: int | None,
    action: str,
    resource: str,
    resource_id: int | str | None,
    metadata: dict[str, Any] | None = None,
) -> AdminAuditLog:
    log = AdminAuditLog(
        admin_user_id=admin_user_id,
        action=action,
        resource=resource,
        resource_id=str(resource_id) if resource_id is not None else None,
        ip_address=request_ip(request),
        user_agent=request.headers.get("user-agent"),
        metadata_json=json.dumps(compact_metadata(metadata), ensure_ascii=False),
    )
    db.add(log)
    return log


def audit_logs_statement(*, action="", resource="", data_inicio="", data_fim=""):
    start_date = parse_date(data_inicio, field="data_inicio")
    end_date = parse_date(data_fim, field="data_fim")
    if start_date and end_date and start_date > end_date:
        raise ValueError("data_inicio nao pode ser maior que data_fim")

    statement = select(AdminAuditLog).options(selectinload(AdminAuditLog.admin_user))
    filters = []
    normalized_action = (action or "").strip()
    normalized_resource = (resource or "").strip()
    if normalized_action:
        filters.append(AdminAuditLog.action == normalized_action)
    if normalized_resource:
        filters.append(AdminAuditLog.resource == normalized_resource)
    start = datetime_start(start_date)
    end = datetime_after(end_date)
    if start:
        filters.append(AdminAuditLog.created_at >= start)
    if end:
        filters.append(AdminAuditLog.created_at < end)
    if filters:
        statement = statement.where(*filters)
    return statement.order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())


def audit_log_payload(log: AdminAuditLog) -> dict[str, Any]:
    data = log.to_dict()
    data["admin_user"] = log.admin_user.to_dict() if log.admin_user else None
    data["admin_email"] = log.admin_user.email if log.admin_user else None
    return data