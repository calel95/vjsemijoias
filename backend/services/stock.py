import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Order, Product, StockMovement
from backend.services.validation import clean_text


STOCK_MOVEMENT_TYPES = {"entrada", "saida", "ajuste"}


def normalize_sku(value) -> str | None:
    sku = clean_text(value, field="sku", max_length=80, required=False).upper()
    return sku or None


def normalize_stock_quantity(value, *, field="stock_quantity", default=0) -> int:
    if value in (None, ""):
        return default
    try:
        quantity = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} deve ser um numero inteiro") from exc
    if quantity < 0:
        raise ValueError(f"{field} nao pode ser negativo")
    return quantity


def normalize_low_stock_alert(value, *, default=1) -> int:
    return normalize_stock_quantity(value, field="low_stock_alert", default=default)


def normalize_stock_movement_type(value) -> str:
    movement_type = clean_text(value, field="tipo", max_length=20, required=True).lower()
    if movement_type not in STOCK_MOVEMENT_TYPES:
        raise ValueError("tipo deve ser entrada, saida ou ajuste")
    return movement_type


def sync_stock_status(product: Product) -> None:
    if product.stock_status == "preorder":
        return
    product.stock_status = "out_of_stock" if (product.stock_quantity or 0) <= 0 else "available"


def has_stock_for(product: Product, quantity: int) -> bool:
    if product.stock_status == "preorder":
        return True
    if product.stock_status == "out_of_stock":
        return False
    return (product.stock_quantity or 0) >= quantity


def ensure_orderable_stock(product: Product, quantity: int) -> None:
    if not has_stock_for(product, quantity):
        raise ValueError(f"Produto sem estoque suficiente: {product.name}")


def product_is_inactive_for_stock(product: Product) -> bool:
    return (product.status or "").lower() == "inativo"


def create_stock_movement(
    db: Session,
    product: Product,
    *,
    tipo,
    quantidade,
    motivo,
    observacoes=None,
    created_by_id=None,
    allow_inactive=False,
) -> StockMovement:
    movement_type = normalize_stock_movement_type(tipo)
    quantity = normalize_stock_quantity(quantidade, field="quantidade")
    if movement_type in {"entrada", "saida"} and quantity <= 0:
        raise ValueError("quantidade deve ser maior que zero")
    if product_is_inactive_for_stock(product) and movement_type != "ajuste" and not allow_inactive:
        raise ValueError("Produto inativo permite apenas ajuste administrativo de estoque")

    reason = clean_text(motivo, field="motivo", max_length=200, required=True)
    notes = clean_text(
        observacoes,
        field="observacoes",
        max_length=2000,
        required=False,
        allow_newlines=True,
    ) or None
    previous_balance = product.stock_quantity or 0

    if movement_type == "entrada":
        current_balance = previous_balance + quantity
    elif movement_type == "saida":
        if quantity > previous_balance:
            raise ValueError("Saida maior que o estoque disponivel")
        current_balance = previous_balance - quantity
    else:
        current_balance = quantity

    if current_balance < 0:
        raise ValueError("Estoque nao pode ficar negativo")

    product.stock_quantity = current_balance
    sync_stock_status(product)
    movement = StockMovement(
        product=product,
        tipo=movement_type,
        quantidade=quantity,
        saldo_anterior=previous_balance,
        saldo_atual=current_balance,
        motivo=reason,
        observacoes=notes,
        created_by_id=created_by_id,
    )
    db.add(movement)
    return movement


def deduct_stock_for_order(db: Session, order: Order) -> bool:
    if order.stock_deducted:
        return False

    try:
        items = json.loads(order.items) if order.items else []
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Itens do pedido invalidos para baixa de estoque") from exc

    quantities_by_product: dict[int, int] = {}
    ordered_product_ids: list[int] = []
    for item in items:
        product_id = int(item["id"])
        quantity = int(item.get("quantity", 1))
        if quantity <= 0:
            raise ValueError("Quantidade do item deve ser maior que zero")
        if product_id not in quantities_by_product:
            ordered_product_ids.append(product_id)
            quantities_by_product[product_id] = 0
        quantities_by_product[product_id] += quantity

    normalized_items: list[tuple[Product, int]] = []
    for product_id in ordered_product_ids:
        product = db.scalar(select(Product).where(Product.id == product_id).with_for_update())
        if not product:
            raise ValueError(f"Produto do pedido nao encontrado: {product_id}")
        quantity = quantities_by_product[product_id]
        ensure_orderable_stock(product, quantity)
        normalized_items.append((product, quantity))

    for product, quantity in normalized_items:
        if product.stock_status == "preorder":
            continue
        create_stock_movement(
            db,
            product,
            tipo="saida",
            quantidade=quantity,
            motivo=f"Pedido publico {order.id} pago",
            observacoes=f"Baixa automatica do pedido publico {order.id}",
        )

    order.stock_deducted = True
    return True
