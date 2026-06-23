import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Order, Product
from backend.services.validation import clean_text


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


def deduct_stock_for_order(db: Session, order: Order) -> bool:
    if order.stock_deducted:
        return False

    try:
        items = json.loads(order.items) if order.items else []
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Itens do pedido invalidos para baixa de estoque") from exc

    for item in items:
        product_id = int(item["id"])
        quantity = int(item.get("quantity", 1))
        product = db.scalar(select(Product).where(Product.id == product_id).with_for_update())
        if not product:
            raise ValueError(f"Produto do pedido nao encontrado: {product_id}")
        ensure_orderable_stock(product, quantity)

    for item in items:
        product = db.get(Product, int(item["id"]))
        if product.stock_status == "preorder":
            continue
        product.stock_quantity = max(0, (product.stock_quantity or 0) - int(item.get("quantity", 1)))
        sync_stock_status(product)

    order.stock_deducted = True
    return True
