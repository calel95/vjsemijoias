from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.database import get_db
from backend.services.vj_dashboard import dashboard_summary


router = APIRouter(prefix="/api/vj-admin", tags=["VJ Admin"])


@router.get("/dashboard")
def get_dashboard(
    periodo: str = Query(default="mes_atual"),
    data_inicio: str = Query(default=""),
    data_fim: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        return dashboard_summary(
            db,
            periodo=periodo,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc