from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.database import get_db
from backend.services.admin_audit import audit_log_payload, audit_logs_statement


router = APIRouter(prefix="/api/vj-admin", tags=["VJ Admin"])


@router.get("/auditoria")
def list_audit_logs(
    action: str = Query(default=""),
    recurso: str = Query(default=""),
    data_inicio: str = Query(default=""),
    data_fim: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        statement = audit_logs_statement(
            action=action,
            resource=recurso,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [audit_log_payload(log) for log in db.scalars(statement).unique().all()]