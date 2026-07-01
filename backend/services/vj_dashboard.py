from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models import Customer, Product
from backend.services.vj_finance import finance_summary, parse_date

PeriodKind = Literal["mes_atual", "ultimos_30_dias", "personalizado"]


def default_period(today: date | None = None) -> tuple[date, date]:
    current = today or datetime.now(UTC).date()
    return current.replace(day=1), current


def resolve_dashboard_period(
    *,
    periodo: str = "mes_atual",
    data_inicio: str = "",
    data_fim: str = "",
    today: date | None = None,
) -> tuple[date, date, str]:
    current = today or datetime.now(UTC).date()
    normalized = (periodo or "mes_atual").strip().lower()

    if normalized == "ultimos_30_dias":
        return current - timedelta(days=29), current, normalized

    if normalized == "personalizado":
        start = parse_date(data_inicio, field="data_inicio", required=True)
        end = parse_date(data_fim, field="data_fim", required=True)
        if start and end and start > end:
            raise ValueError("data_inicio nao pode ser maior que data_fim")
        return start, end, normalized

    if normalized not in {"", "mes_atual"}:
        raise ValueError("Periodo de dashboard invalido")

    start, end = default_period(current)
    return start, end, "mes_atual"


def product_operational_summary(db: Session) -> dict[str, int]:
    active_public = db.scalar(
        select(func.count(Product.id)).where(
            Product.publicado.is_(True),
            Product.is_active.is_(True),
            Product.status != "inativo",
        )
    ) or 0
    low_stock = db.scalar(
        select(func.count(Product.id)).where(
            Product.is_active.is_(True),
            Product.status != "inativo",
            Product.stock_quantity > 0,
            Product.stock_quantity <= Product.low_stock_alert,
            Product.stock_status != "out_of_stock",
        )
    ) or 0
    out_of_stock = db.scalar(
        select(func.count(Product.id)).where(
            Product.is_active.is_(True),
            Product.status != "inativo",
            (Product.stock_quantity <= 0) | (Product.stock_status == "out_of_stock"),
        )
    ) or 0
    return {
        "produtos_ativos_publicados": int(active_public),
        "produtos_estoque_baixo": int(low_stock),
        "produtos_sem_estoque": int(out_of_stock),
    }


def customer_operational_summary(db: Session) -> dict[str, int]:
    active_customers = db.scalar(
        select(func.count(Customer.id)).where(Customer.status == "ativo")
    ) or 0
    return {"clientes_ativos": int(active_customers)}


def dashboard_summary(
    db: Session,
    *,
    periodo: str = "mes_atual",
    data_inicio: str = "",
    data_fim: str = "",
) -> dict:
    start, end, normalized_period = resolve_dashboard_period(
        periodo=periodo,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )
    summary = finance_summary(db, data_inicio=start.isoformat(), data_fim=end.isoformat())
    top_products = sorted(
        summary["ranking_produtos"],
        key=lambda item: (item.get("faturamento") or 0, item.get("quantidade") or 0),
        reverse=True,
    )[:5]
    top_clients = sorted(
        summary["ranking_clientes"],
        key=lambda item: (item.get("total") or 0, item.get("quantidade_pedidos") or 0),
        reverse=True,
    )[:5]
    return {
        "periodo": normalized_period,
        "data_inicio": start.isoformat(),
        "data_fim": end.isoformat(),
        "faturamento_mes": summary["faturamento_bruto"],
        "lucro_liquido_estimado_mes": summary["lucro_liquido_estimado"],
        "pedidos_confirmados_mes": summary["quantidade_pedidos_confirmados"],
        "ticket_medio_mes": summary["ticket_medio"],
        "despesas_mes": summary["despesas"],
        "margem_liquida_estimada": summary["margem_liquida_estimada"],
        "top_produtos": top_products,
        "top_clientes": top_clients,
        "resumo_pagamentos": summary["resumo_pagamentos"],
        **customer_operational_summary(db),
        **product_operational_summary(db),
    }