from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.database import get_db
from backend.models import Supplier
from backend.services.common import get_or_404
from backend.services.vj_products import apply_supplier_fields, supplier_payload


router = APIRouter(prefix="/api/vj-admin", tags=["VJ Admin"])


@router.get("/fornecedores")
def list_suppliers(
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    suppliers = db.scalars(select(Supplier).order_by(Supplier.nome, Supplier.id)).all()
    return [supplier.to_dict() for supplier in suppliers]


@router.post("/fornecedores", status_code=201)
def create_supplier(
    data: dict[str, Any] = Body(default_factory=dict),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        cleaned = supplier_payload(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    supplier = Supplier(**cleaned)
    db.add(supplier)
    db.commit()
    return supplier.to_dict()


@router.put("/fornecedores/{supplier_id}")
def update_supplier(
    supplier_id: int,
    data: dict[str, Any] = Body(default_factory=dict),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    supplier = get_or_404(db, Supplier, supplier_id)
    try:
        cleaned = supplier_payload(data, partial=True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    apply_supplier_fields(supplier, cleaned)
    db.commit()
    return supplier.to_dict()