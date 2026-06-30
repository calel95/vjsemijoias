from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.database import get_db
from backend.models import Customer
from backend.routers.vj_admin_common import admin_user_id
from backend.services.common import get_or_404
from backend.services.vj_customers import (
    create_customer,
    customer_orders_payload,
    customers_statement,
    deactivate_customer,
    update_customer,
)


router = APIRouter(prefix="/api/vj-admin", tags=["VJ Admin"])


@router.get("/clientes")
def list_customers(
    search: str = Query(default=""),
    status: str = Query(default=""),
    cidade: str = Query(default=""),
    origem: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        statement = customers_statement(search=search, status=status, cidade=cidade, origem=origem)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    customers = db.scalars(statement).unique().all()
    return [customer.to_dict() for customer in customers]


@router.get("/clientes/{customer_id}")
def get_customer(
    customer_id: int,
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    return get_or_404(db, Customer, customer_id).to_dict()


@router.post("/clientes", status_code=201)
def create_customer_endpoint(
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        customer = create_customer(db, data, actor_id=admin_user_id(claims))
        db.flush()
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return customer.to_dict()


@router.put("/clientes/{customer_id}")
def update_customer_endpoint(
    customer_id: int,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    customer = get_or_404(db, Customer, customer_id)
    try:
        update_customer(db, customer, data, actor_id=admin_user_id(claims))
        db.flush()
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return customer.to_dict()


@router.post("/clientes/{customer_id}/inativar")
def deactivate_customer_endpoint(
    customer_id: int,
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    customer = get_or_404(db, Customer, customer_id)
    deactivate_customer(customer, actor_id=admin_user_id(claims))
    db.commit()
    return customer.to_dict()


@router.get("/clientes/{customer_id}/pedidos")
def list_customer_orders(
    customer_id: int,
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    customer = get_or_404(db, Customer, customer_id)
    return customer_orders_payload(db, customer)