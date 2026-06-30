import csv
from io import StringIO
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.database import get_db
from backend.models import Customer
from backend.routers.vj_admin_common import admin_user_id
from backend.services.admin_audit import record_vj_admin_audit
from backend.services.common import get_or_404
from backend.services.vj_customers import (
    create_customer,
    customer_orders_payload,
    customers_statement,
    deactivate_customer,
    update_customer,
)


router = APIRouter(prefix="/api/vj-admin", tags=["VJ Admin"])

CUSTOMER_CSV_FIELDS = [
    "id",
    "nome",
    "whatsapp",
    "email",
    "cpf",
    "instagram",
    "cidade",
    "estado",
    "data_nascimento",
    "origem",
    "status",
    "created_at",
    "updated_at",
]


def customer_csv_row(customer: Customer):
    data = customer.to_dict()
    return {field: data.get(field) for field in CUSTOMER_CSV_FIELDS}


def filtered_customers(db: Session, *, search="", status="", cidade="", origem=""):
    try:
        statement = customers_statement(search=search, status=status, cidade=cidade, origem=origem)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return db.scalars(statement).unique().all()


@router.get("/clientes")
def list_customers(
    search: str = Query(default=""),
    status: str = Query(default=""),
    cidade: str = Query(default=""),
    origem: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    return [customer.to_dict() for customer in filtered_customers(db, search=search, status=status, cidade=cidade, origem=origem)]


@router.get("/clientes/export.csv")
def export_customers_csv(
    search: str = Query(default=""),
    status: str = Query(default=""),
    cidade: str = Query(default=""),
    origem: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    output = StringIO()
    output.write("\ufeff")
    writer = csv.DictWriter(output, fieldnames=CUSTOMER_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for customer in filtered_customers(db, search=search, status=status, cidade=cidade, origem=origem):
        writer.writerow(customer_csv_row(customer))
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="vj-admin-clientes.csv"'},
    )


@router.get("/clientes/{customer_id}")
def get_customer(
    customer_id: int,
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    return get_or_404(db, Customer, customer_id).to_dict()


@router.post("/clientes", status_code=201)
def create_customer_endpoint(
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    actor_id = admin_user_id(claims)
    try:
        customer = create_customer(db, data, actor_id=actor_id)
        db.flush()
        record_vj_admin_audit(
            db,
            request,
            admin_user_id=actor_id,
            action="cliente_criado",
            resource="cliente",
            resource_id=customer.id,
            metadata={"nome": customer.nome, "status": customer.status, "origem": customer.origem},
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return customer.to_dict()


@router.put("/clientes/{customer_id}")
def update_customer_endpoint(
    customer_id: int,
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    customer = get_or_404(db, Customer, customer_id)
    actor_id = admin_user_id(claims)
    try:
        update_customer(db, customer, data, actor_id=actor_id)
        db.flush()
        record_vj_admin_audit(
            db,
            request,
            admin_user_id=actor_id,
            action="cliente_atualizado",
            resource="cliente",
            resource_id=customer.id,
            metadata={"nome": customer.nome, "status": customer.status, "campos": sorted(data.keys())},
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return customer.to_dict()


@router.post("/clientes/{customer_id}/inativar")
def deactivate_customer_endpoint(
    customer_id: int,
    request: Request,
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    customer = get_or_404(db, Customer, customer_id)
    actor_id = admin_user_id(claims)
    deactivate_customer(customer, actor_id=actor_id)
    db.flush()
    record_vj_admin_audit(
        db,
        request,
        admin_user_id=actor_id,
        action="cliente_inativado",
        resource="cliente",
        resource_id=customer.id,
        metadata={"nome": customer.nome, "status": customer.status},
    )
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