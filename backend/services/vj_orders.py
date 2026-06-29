from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Product, VJAdminOrder, VJAdminOrderItem
from backend.services.pricing import MONEY_QUANT, PAYMENT_FEES, RATIO_QUANT, money as money_value
from backend.services.stock import create_stock_movement, ensure_orderable_stock
from backend.services.validation import clean_text, normalize_phone


ORDER_STATUSES = {"rascunho", "confirmado", "cancelado"}
PAYMENT_METHODS = {"pix", "debito", "credito"}


def normalize_payment_method(value) -> str:
    method = clean_text(value or "pix", field="forma_pagamento", max_length=30, required=True).lower()
    if method not in PAYMENT_METHODS:
        raise ValueError("forma_pagamento deve ser pix, debito ou credito")
    return method


def normalize_installments(value, payment_method: str) -> int:
    if value in (None, ""):
        value = 1
    try:
        installments = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("parcelas deve ser um numero inteiro") from exc
    if payment_method in {"pix", "debito"}:
        return 1
    if installments < 1 or installments > 12:
        raise ValueError("parcelas deve estar entre 1 e 12")
    return installments


def price_field_for_payment(payment_method: str, installments: int) -> str:
    if payment_method == "pix":
        return "preco_pix"
    if payment_method == "debito":
        return "preco_debito"
    if installments <= 1:
        return "preco_credito_vista"
    return f"preco_credito_{installments}x"


def payment_fee(payment_method: str, installments: int) -> Decimal:
    return PAYMENT_FEES[price_field_for_payment(payment_method, installments)]


def normalize_order_items(items: Any) -> list[dict[str, int]]:
    if not isinstance(items, list) or not items:
        raise ValueError("Pedido deve conter ao menos um item")
    quantities: dict[int, int] = {}
    ordered_ids: list[int] = []
    for item in items:
        try:
            product_id = int(item.get("produto_id", item.get("product_id", item.get("id"))))
            quantity = int(item.get("quantidade", item.get("quantity", 1)))
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("Item do pedido invalido") from exc
        if quantity < 1:
            raise ValueError("quantidade deve ser maior que zero")
        if product_id not in quantities:
            ordered_ids.append(product_id)
            quantities[product_id] = 0
        quantities[product_id] += quantity
    return [{"produto_id": product_id, "quantidade": quantities[product_id]} for product_id in ordered_ids]


def product_unit_price(product: Product, payment_method: str, installments: int) -> Decimal:
    field = price_field_for_payment(payment_method, installments)
    value = getattr(product, field, None) or product.price
    return money_value(value, field=field)


def product_unit_cost(product: Product) -> Decimal:
    value = product.custo_total or (product.custo_peca or Decimal("0.00")) + (product.custo_embalagem or Decimal("0.00"))
    return money_value(value, field="custo_unitario", default=Decimal("0.00"))


def allocate_amount(amount: Decimal, weights: list[Decimal]) -> list[Decimal]:
    amount = amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    total_weight = sum(weights, Decimal("0.00"))
    if not weights:
        return []
    if amount == Decimal("0.00") or total_weight == Decimal("0.00"):
        return [Decimal("0.00") for _ in weights]
    allocations: list[Decimal] = []
    allocated = Decimal("0.00")
    for index, weight in enumerate(weights):
        if index == len(weights) - 1:
            share = (amount - allocated).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        else:
            share = (amount * weight / total_weight).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            allocated += share
        allocations.append(share)
    return allocations


def refresh_order_for_update(db: Session, order: VJAdminOrder) -> None:
    if order.id is not None:
        db.refresh(order, with_for_update=True)


def calculate_order_values(
    db: Session,
    *,
    items,
    forma_pagamento,
    parcelas,
    desconto_total=0,
):
    payment_method = normalize_payment_method(forma_pagamento)
    installments = normalize_installments(parcelas, payment_method)
    normalized_items = normalize_order_items(items)
    product_ids = [item["produto_id"] for item in normalized_items]
    products = db.scalars(select(Product).where(Product.id.in_(product_ids))).unique().all()
    products_by_id = {product.id: product for product in products}
    if len(products_by_id) != len(product_ids):
        raise ValueError("Um ou mais produtos nao foram encontrados")

    fee = payment_fee(payment_method, installments)
    rows = []
    subtotal = Decimal("0.00")
    cost_total = Decimal("0.00")
    for item in normalized_items:
        product = products_by_id[item["produto_id"]]
        if (product.status or "").lower() == "inativo":
            raise ValueError("Produto inativo nao pode ser adicionado ao pedido")
        quantity = item["quantidade"]
        unit_price = product_unit_price(product, payment_method, installments)
        unit_cost = product_unit_cost(product)
        item_total = (unit_price * quantity).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        item_cost_total = (unit_cost * quantity).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        subtotal += item_total
        cost_total += item_cost_total
        rows.append(
            {
                "produto_id": product.id,
                "quantidade": quantity,
                "unit_price": unit_price,
                "unit_cost": unit_cost,
                "item_total": item_total,
                "cost_total": item_cost_total,
            }
        )

    subtotal = subtotal.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    discount = money_value(desconto_total, field="desconto_total", default=Decimal("0.00"))
    if discount > subtotal:
        raise ValueError("desconto_total nao pode ser maior que o subtotal")
    total = (subtotal - discount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    payment_tax = (total * fee / Decimal("100")).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    estimated_profit = (total - payment_tax - cost_total).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
    estimated_margin = (
        (estimated_profit / total).quantize(RATIO_QUANT, rounding=ROUND_HALF_UP)
        if total
        else Decimal("0.0000")
    )

    discount_allocations = allocate_amount(discount, [row["item_total"] for row in rows])
    discounted_totals = [
        (row["item_total"] - discount_allocations[index]).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        for index, row in enumerate(rows)
    ]
    tax_allocations = allocate_amount(payment_tax, discounted_totals)

    order_items = []
    for index, row in enumerate(rows):
        item_profit = (
            discounted_totals[index] - tax_allocations[index] - row["cost_total"]
        ).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
        unit_profit = (item_profit / Decimal(row["quantidade"])).quantize(
            MONEY_QUANT,
            rounding=ROUND_HALF_UP,
        )
        order_items.append(
            VJAdminOrderItem(
                produto_id=row["produto_id"],
                quantidade=row["quantidade"],
                preco_unitario=row["unit_price"],
                custo_unitario=row["unit_cost"],
                taxa_percentual=fee,
                lucro_unitario=unit_profit,
                total_item=row["item_total"],
            )
        )

    return {
        "forma_pagamento": payment_method,
        "parcelas": installments,
        "desconto_total": discount,
        "subtotal": subtotal,
        "taxa_pagamento": payment_tax,
        "total": total,
        "lucro_estimado": estimated_profit,
        "margem_estimada": estimated_margin,
        "items": order_items,
    }


def apply_order_payload(order: VJAdminOrder, db: Session, data: dict[str, Any], *, actor_id: int | None):
    if order.status != "rascunho":
        raise ValueError("Nao e permitido editar itens de pedido confirmado ou cancelado")
    customer_name = clean_text(data.get("cliente_nome"), field="cliente_nome", max_length=200, required=True)
    customer_whatsapp = normalize_phone(data.get("cliente_whatsapp"), required=False)
    values = calculate_order_values(
        db,
        items=data.get("items", []),
        forma_pagamento=data.get("forma_pagamento", order.forma_pagamento or "pix"),
        parcelas=data.get("parcelas", order.parcelas or 1),
        desconto_total=data.get("desconto_total", 0),
    )
    order.cliente_nome = customer_name
    order.cliente_whatsapp = customer_whatsapp
    order.forma_pagamento = values["forma_pagamento"]
    order.parcelas = values["parcelas"]
    order.desconto_total = values["desconto_total"]
    order.subtotal = values["subtotal"]
    order.taxa_pagamento = values["taxa_pagamento"]
    order.total = values["total"]
    order.lucro_estimado = values["lucro_estimado"]
    order.margem_estimada = values["margem_estimada"]
    order.updated_by_id = actor_id
    order.items.clear()
    order.items.extend(values["items"])
    return order


def create_vj_admin_order(db: Session, data: dict[str, Any], *, actor_id: int | None) -> VJAdminOrder:
    order = VJAdminOrder(
        cliente_nome="",
        cliente_whatsapp=None,
        forma_pagamento="pix",
        parcelas=1,
        status="rascunho",
        created_by_id=actor_id,
        updated_by_id=actor_id,
    )
    db.add(order)
    apply_order_payload(order, db, data, actor_id=actor_id)
    return order


def update_vj_admin_order(db: Session, order: VJAdminOrder, data: dict[str, Any], *, actor_id: int | None):
    return apply_order_payload(order, db, data, actor_id=actor_id)


def confirm_vj_admin_order(db: Session, order: VJAdminOrder, *, actor_id: int | None) -> VJAdminOrder:
    refresh_order_for_update(db, order)
    if order.status == "confirmado":
        raise ValueError("Pedido confirmado nao pode ser confirmado novamente")
    if order.status == "cancelado":
        raise ValueError("Pedido cancelado nao pode ser confirmado")
    if not order.items:
        raise ValueError("Pedido deve conter ao menos um item")

    locked_products = {}
    for item in order.items:
        product = db.scalar(select(Product).where(Product.id == item.produto_id).with_for_update())
        if product is None:
            raise ValueError("Produto do pedido nao encontrado")
        ensure_orderable_stock(product, item.quantidade)
        locked_products[item.produto_id] = product

    for item in order.items:
        create_stock_movement(
            db,
            locked_products[item.produto_id],
            tipo="saida",
            quantidade=item.quantidade,
            motivo=f"Pedido VJ Admin #{order.id} confirmado",
            observacoes=order.cliente_nome,
            created_by_id=actor_id,
        )
    order.status = "confirmado"
    order.updated_by_id = actor_id
    return order


def cancel_vj_admin_order(db: Session, order: VJAdminOrder, *, actor_id: int | None) -> VJAdminOrder:
    refresh_order_for_update(db, order)
    if order.status == "cancelado":
        raise ValueError("Pedido cancelado nao pode ser cancelado novamente")
    if order.status == "confirmado":
        for item in order.items:
            product = db.scalar(select(Product).where(Product.id == item.produto_id).with_for_update())
            if product is None:
                raise ValueError("Produto do pedido nao encontrado")
            create_stock_movement(
                db,
                product,
                tipo="entrada",
                quantidade=item.quantidade,
                motivo=f"Pedido VJ Admin #{order.id} cancelado",
                observacoes=order.cliente_nome,
                created_by_id=actor_id,
                allow_inactive=True,
            )
    order.status = "cancelado"
    order.updated_by_id = actor_id
    return order
