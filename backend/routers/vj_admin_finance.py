import csv
from io import StringIO
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.database import get_db
from backend.models import Expense
from backend.routers.vj_admin_common import admin_user_id
from backend.services.admin_audit import record_vj_admin_audit
from backend.services.common import get_or_404
from backend.services.vj_finance import (
    cancel_expense,
    create_expense,
    expenses_statement,
    finance_summary,
    update_expense,
)


router = APIRouter(prefix="/api/vj-admin", tags=["VJ Admin"])

EXPENSE_CSV_FIELDS = [
    "id",
    "descricao",
    "categoria",
    "valor",
    "data",
    "status",
    "observacoes",
    "created_at",
    "updated_at",
    "created_by",
    "updated_by",
]

SUMMARY_CSV_FIELDS = ["secao", "chave", "valor", "quantidade", "extra"]


def expense_csv_row(expense: Expense):
    data = expense.to_dict()
    return {
        **{field: data.get(field) for field in EXPENSE_CSV_FIELDS},
        "created_by": (data.get("created_by") or {}).get("email") or "",
        "updated_by": (data.get("updated_by") or {}).get("email") or "",
    }


def filtered_expenses(db: Session, *, data_inicio="", data_fim="", status="", categoria=""):
    try:
        statement = expenses_statement(
            data_inicio=data_inicio,
            data_fim=data_fim,
            status=status,
            categoria=categoria,
            include_audit=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return db.scalars(statement).unique().all()


def summary_csv_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {"secao": "indicador", "chave": "faturamento_bruto", "valor": summary["faturamento_bruto"]},
        {"secao": "indicador", "chave": "total_descontos", "valor": summary["total_descontos"]},
        {"secao": "indicador", "chave": "taxas_pagamento", "valor": summary["taxas_pagamento"]},
        {"secao": "indicador", "chave": "custo_produtos_vendidos", "valor": summary["custo_produtos_vendidos"]},
        {"secao": "indicador", "chave": "lucro_bruto", "valor": summary["lucro_bruto"]},
        {"secao": "indicador", "chave": "despesas", "valor": summary["despesas"]},
        {"secao": "indicador", "chave": "lucro_liquido_estimado", "valor": summary["lucro_liquido_estimado"]},
        {"secao": "indicador", "chave": "margem_liquida_estimada", "valor": summary["margem_liquida_estimada"]},
        {"secao": "indicador", "chave": "quantidade_pedidos_confirmados", "quantidade": summary["quantidade_pedidos_confirmados"]},
        {"secao": "indicador", "chave": "ticket_medio", "valor": summary["ticket_medio"]},
    ]
    for item in summary.get("ranking_produtos", []):
        rows.append({
            "secao": "ranking_produtos",
            "chave": item.get("codigo") or item.get("produto_id"),
            "valor": item.get("faturamento"),
            "quantidade": item.get("quantidade"),
            "extra": item.get("nome"),
        })
    for item in summary.get("ranking_clientes", []):
        rows.append({
            "secao": "ranking_clientes",
            "chave": item.get("customer_id") or item.get("nome"),
            "valor": item.get("total"),
            "quantidade": item.get("quantidade_pedidos"),
            "extra": item.get("nome"),
        })
    for item in summary.get("resumo_pagamentos", []):
        rows.append({
            "secao": "resumo_pagamentos",
            "chave": item.get("forma_pagamento"),
            "valor": item.get("faturamento"),
            "quantidade": item.get("quantidade_pedidos"),
            "extra": f"taxas={item.get('taxas')} lucro={item.get('lucro_bruto')}",
        })
    return rows


@router.get("/financeiro/resumo")
def get_finance_summary(
    data_inicio: str = Query(default=""),
    data_fim: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        return finance_summary(db, data_inicio=data_inicio, data_fim=data_fim)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/financeiro/resumo/export.csv")
def export_finance_summary_csv(
    data_inicio: str = Query(default=""),
    data_fim: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    try:
        summary = finance_summary(db, data_inicio=data_inicio, data_fim=data_fim)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    output = StringIO()
    output.write("\ufeff")
    writer = csv.DictWriter(output, fieldnames=SUMMARY_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(summary_csv_rows(summary))
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="vj-admin-financeiro-resumo.csv"'},
    )


@router.get("/financeiro/despesas")
def list_expenses(
    data_inicio: str = Query(default=""),
    data_fim: str = Query(default=""),
    status: str = Query(default=""),
    categoria: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    return [expense.to_dict() for expense in filtered_expenses(db, data_inicio=data_inicio, data_fim=data_fim, status=status, categoria=categoria)]


@router.get("/financeiro/despesas/export.csv")
def export_expenses_csv(
    data_inicio: str = Query(default=""),
    data_fim: str = Query(default=""),
    status: str = Query(default=""),
    categoria: str = Query(default=""),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    output = StringIO()
    output.write("\ufeff")
    writer = csv.DictWriter(output, fieldnames=EXPENSE_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    for expense in filtered_expenses(db, data_inicio=data_inicio, data_fim=data_fim, status=status, categoria=categoria):
        writer.writerow(expense_csv_row(expense))
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="vj-admin-despesas.csv"'},
    )


@router.post("/financeiro/despesas", status_code=201)
def create_expense_endpoint(
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    actor_id = admin_user_id(claims)
    try:
        expense = create_expense(db, data, actor_id=actor_id)
        db.flush()
        record_vj_admin_audit(
            db,
            request,
            admin_user_id=actor_id,
            action="despesa_criada",
            resource="despesa",
            resource_id=expense.id,
            metadata={"descricao": expense.descricao, "categoria": expense.categoria, "valor": float(expense.valor or 0)},
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return expense.to_dict()


@router.put("/financeiro/despesas/{expense_id}")
def update_expense_endpoint(
    expense_id: int,
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    expense = get_or_404(db, Expense, expense_id)
    actor_id = admin_user_id(claims)
    try:
        update_expense(expense, data, actor_id=actor_id)
        db.flush()
        record_vj_admin_audit(
            db,
            request,
            admin_user_id=actor_id,
            action="despesa_atualizada",
            resource="despesa",
            resource_id=expense.id,
            metadata={"descricao": expense.descricao, "categoria": expense.categoria, "valor": float(expense.valor or 0), "campos": sorted(data.keys())},
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return expense.to_dict()


@router.post("/financeiro/despesas/{expense_id}/cancelar")
def cancel_expense_endpoint(
    expense_id: int,
    request: Request,
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    expense = get_or_404(db, Expense, expense_id)
    actor_id = admin_user_id(claims)
    cancel_expense(expense, actor_id=actor_id)
    db.flush()
    record_vj_admin_audit(
        db,
        request,
        admin_user_id=actor_id,
        action="despesa_cancelada",
        resource="despesa",
        resource_id=expense.id,
        metadata={"descricao": expense.descricao, "categoria": expense.categoria, "valor": float(expense.valor or 0)},
    )
    db.commit()
    return expense.to_dict()