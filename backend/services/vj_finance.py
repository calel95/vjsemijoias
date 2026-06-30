from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.models import Expense, VJAdminOrder, VJAdminOrderItem
from backend.models.base import decimal_to_float
from backend.services.pricing import MONEY_QUANT, money as money_value
from backend.services.validation import clean_text

EXPENSE_STATUSES = {"ativo", "cancelado"}


def parse_date(value, *, field: str, required=False) -> date | None:
    if value in (None, ""):
        if required:
            raise ValueError(f"Campo obrigatorio: {field}")
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise ValueError(f"{field} invalida") from exc


def datetime_start(value: date | None) -> datetime | None:
    return datetime.combine(value, time.min, tzinfo=UTC) if value else None


def datetime_after(value: date | None) -> datetime | None:
    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=UTC) if value else None


def normalize_expense_status(value, *, default="ativo") -> str:
    status = clean_text(value or default, field="status", max_length=30, required=True).lower()
    if status not in EXPENSE_STATUSES:
        raise ValueError("Status de despesa invalido")
    return status


def expense_payload(data: dict[str, Any], *, partial=False) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if not partial or "descricao" in data:
        payload["descricao"] = clean_text(data.get("descricao"), field="descricao", max_length=200, required=not partial)
    if not partial or "categoria" in data:
        payload["categoria"] = clean_text(data.get("categoria"), field="categoria", max_length=120, required=not partial)
    if not partial or "valor" in data:
        payload["valor"] = money_value(data.get("valor"), field="valor")
        if payload["valor"] <= Decimal("0.00"):
            raise ValueError("valor deve ser maior que zero")
    if not partial or "data" in data:
        payload["data"] = parse_date(data.get("data"), field="data", required=not partial)
    if not partial or "observacoes" in data:
        notes = clean_text(data.get("observacoes"), field="observacoes", max_length=2000, allow_newlines=True)
        payload["observacoes"] = notes or None
    if not partial or "status" in data:
        payload["status"] = normalize_expense_status(data.get("status"), default="ativo")
    if partial:
        payload = {key: value for key, value in payload.items() if key in data}
    return payload


def create_expense(db: Session, data: dict[str, Any], *, actor_id: int | None) -> Expense:
    expense = Expense(**expense_payload(data), created_by_id=actor_id, updated_by_id=actor_id)
    db.add(expense)
    return expense


def update_expense(expense: Expense, data: dict[str, Any], *, actor_id: int | None) -> Expense:
    for field, value in expense_payload(data, partial=True).items():
        setattr(expense, field, value)
    expense.updated_by_id = actor_id
    return expense


def cancel_expense(expense: Expense, *, actor_id: int | None) -> Expense:
    expense.status = "cancelado"
    expense.updated_by_id = actor_id
    return expense


def expenses_statement(*, data_inicio="", data_fim="", status="", categoria="", include_audit=False):
    start = parse_date(data_inicio, field="data_inicio")
    end = parse_date(data_fim, field="data_fim")
    if start and end and start > end:
        raise ValueError("data_inicio nao pode ser maior que data_fim")
    statement = select(Expense)
    if include_audit:
        statement = statement.options(selectinload(Expense.created_by), selectinload(Expense.updated_by))
    filters = []
    if start:
        filters.append(Expense.data >= start)
    if end:
        filters.append(Expense.data <= end)
    normalized_status = (status or "").strip().lower()
    if normalized_status:
        if normalized_status not in EXPENSE_STATUSES:
            raise ValueError("Status de despesa invalido")
        filters.append(Expense.status == normalized_status)
    normalized_category = clean_text(categoria, field="categoria", max_length=120).lower()
    if normalized_category:
        filters.append(Expense.categoria.ilike(normalized_category))
    if filters:
        statement = statement.where(*filters)
    return statement.order_by(Expense.data.desc(), Expense.id.desc())


def confirmed_orders_statement(*, data_inicio="", data_fim=""):
    start_date = parse_date(data_inicio, field="data_inicio")
    end_date = parse_date(data_fim, field="data_fim")
    if start_date and end_date and start_date > end_date:
        raise ValueError("data_inicio nao pode ser maior que data_fim")
    statement = (
        select(VJAdminOrder)
        .options(
            selectinload(VJAdminOrder.items).selectinload(VJAdminOrderItem.produto),
            selectinload(VJAdminOrder.customer),
        )
        .where(VJAdminOrder.status == "confirmado")
    )
    start = datetime_start(start_date)
    end = datetime_after(end_date)
    if start:
        statement = statement.where(VJAdminOrder.created_at >= start)
    if end:
        statement = statement.where(VJAdminOrder.created_at < end)
    return statement.order_by(VJAdminOrder.id.desc())


def money_float(value: Decimal) -> float:
    return decimal_to_float(value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP))


def finance_summary(db: Session, *, data_inicio="", data_fim="") -> dict[str, Any]:
    orders = db.scalars(confirmed_orders_statement(data_inicio=data_inicio, data_fim=data_fim)).unique().all()
    expenses = db.scalars(
        expenses_statement(data_inicio=data_inicio, data_fim=data_fim, status="ativo")
    ).unique().all()

    gross_revenue = sum((order.subtotal or Decimal("0.00") for order in orders), Decimal("0.00"))
    discounts = sum((order.desconto_total or Decimal("0.00") for order in orders), Decimal("0.00"))
    payment_fees = sum((order.taxa_pagamento or Decimal("0.00") for order in orders), Decimal("0.00"))
    net_revenue = sum((order.total or Decimal("0.00") for order in orders), Decimal("0.00"))
    sold_cost = sum(
        (
            (item.custo_unitario or Decimal("0.00")) * Decimal(item.quantidade or 0)
            for order in orders
            for item in order.items
        ),
        Decimal("0.00"),
    ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    gross_profit = (net_revenue - payment_fees - sold_cost).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    expense_total = sum((expense.valor or Decimal("0.00") for expense in expenses), Decimal("0.00"))
    net_profit = (gross_profit - expense_total).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    order_count = len(orders)
    average_ticket = (net_revenue / order_count).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP) if order_count else Decimal("0.00")
    net_margin = (net_profit / net_revenue).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if net_revenue else Decimal("0.0000")

    products: dict[int, dict[str, Any]] = {}
    clients: dict[str, dict[str, Any]] = {}
    payment_methods: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "forma_pagamento": "",
        "quantidade_pedidos": 0,
        "faturamento": Decimal("0.00"),
        "taxas": Decimal("0.00"),
        "lucro_bruto": Decimal("0.00"),
    })

    for order in orders:
        payment_key = order.forma_pagamento or "pix"
        payment_row = payment_methods[payment_key]
        payment_row["forma_pagamento"] = payment_key
        payment_row["quantidade_pedidos"] += 1
        payment_row["faturamento"] += order.total or Decimal("0.00")
        payment_row["taxas"] += order.taxa_pagamento or Decimal("0.00")
        payment_row["lucro_bruto"] += order.lucro_estimado or Decimal("0.00")

        client_key = f"customer:{order.customer_id}" if order.customer_id else f"manual:{(order.cliente_nome or '').lower()}:{order.cliente_whatsapp or ''}"
        client_row = clients.setdefault(client_key, {
            "customer_id": order.customer_id,
            "nome": order.customer.nome if order.customer else order.cliente_nome,
            "whatsapp": order.customer.whatsapp if order.customer else order.cliente_whatsapp,
            "quantidade_pedidos": 0,
            "total": Decimal("0.00"),
            "ultima_compra": None,
        })
        client_row["quantidade_pedidos"] += 1
        client_row["total"] += order.total or Decimal("0.00")
        last_date = order.updated_at or order.created_at
        if last_date and (client_row["ultima_compra"] is None or last_date > client_row["ultima_compra"]):
            client_row["ultima_compra"] = last_date

        for item in order.items:
            product = item.produto
            product_id = item.produto_id
            row = products.setdefault(product_id, {
                "produto_id": product_id,
                "codigo": product.codigo if product else None,
                "nome": product.name if product else f"Produto {product_id}",
                "quantidade": 0,
                "faturamento": Decimal("0.00"),
                "custo": Decimal("0.00"),
                "lucro_bruto": Decimal("0.00"),
            })
            quantity = int(item.quantidade or 0)
            revenue = (item.total_item or Decimal("0.00")).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            cost = ((item.custo_unitario or Decimal("0.00")) * Decimal(quantity)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            item_profit = ((item.lucro_unitario or Decimal("0.00")) * Decimal(quantity)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            row["quantidade"] += quantity
            row["faturamento"] += revenue
            row["custo"] += cost
            row["lucro_bruto"] += item_profit

    product_ranking = sorted(products.values(), key=lambda item: (item["quantidade"], item["faturamento"]), reverse=True)
    client_ranking = sorted(clients.values(), key=lambda item: (item["total"], item["quantidade_pedidos"]), reverse=True)
    payment_summary = sorted(payment_methods.values(), key=lambda item: item["faturamento"], reverse=True)

    for row in product_ranking:
        row["faturamento"] = money_float(row["faturamento"])
        row["custo"] = money_float(row["custo"])
        row["lucro_bruto"] = money_float(row["lucro_bruto"])
    for row in client_ranking:
        row["total"] = money_float(row["total"])
        row["ticket_medio"] = money_float(Decimal(str(row["total"])) / row["quantidade_pedidos"]) if row["quantidade_pedidos"] else 0.0
        row["ultima_compra"] = row["ultima_compra"].isoformat() if row["ultima_compra"] else None
    for row in payment_summary:
        row["faturamento"] = money_float(row["faturamento"])
        row["taxas"] = money_float(row["taxas"])
        row["lucro_bruto"] = money_float(row["lucro_bruto"])

    return {
        "filtros": {"data_inicio": data_inicio or None, "data_fim": data_fim or None},
        "faturamento_bruto": money_float(gross_revenue),
        "total_descontos": money_float(discounts),
        "taxas_pagamento": money_float(payment_fees),
        "custo_produtos_vendidos": money_float(sold_cost),
        "lucro_bruto": money_float(gross_profit),
        "despesas": money_float(expense_total),
        "lucro_liquido_estimado": money_float(net_profit),
        "margem_liquida_estimada": decimal_to_float(net_margin),
        "quantidade_pedidos_confirmados": order_count,
        "ticket_medio": money_float(average_ticket),
        "ranking_produtos": product_ranking,
        "ranking_clientes": client_ranking,
        "resumo_pagamentos": payment_summary,
    }
