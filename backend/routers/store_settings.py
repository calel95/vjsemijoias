from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.database import get_db
from backend.store_config import admin_store_config, update_store_settings


router = APIRouter(prefix="/api/admin/store-config", tags=["Admin - Store Config"])


@router.get("")
def get_admin_store_config(
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    return admin_store_config(db)


@router.put("")
def update_admin_store_config(
    data: dict[str, Any] = Body(default_factory=dict),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        return update_store_settings(db, data.get("values", data))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
