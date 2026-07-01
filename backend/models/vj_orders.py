from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, MONEY_COLUMN, PERCENT_COLUMN, RATIO_COLUMN, decimal_to_float, utc_now


class VJAdminOrder(Base):
    __tablename__ = "vj_admin_pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), index=True, nullable=True)
    cliente_nome: Mapped[str] = mapped_column(String(200))
    cliente_whatsapp: Mapped[str | None] = mapped_column(String(30), nullable=True)
    forma_pagamento: Mapped[str] = mapped_column(String(30), default="pix")
    parcelas: Mapped[int] = mapped_column(Integer, default=1)
    desconto_total: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    subtotal: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    taxa_pagamento: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    lucro_estimado: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    margem_estimada: Mapped[Decimal] = mapped_column(RATIO_COLUMN, default=Decimal("0.0000"))
    status: Mapped[str] = mapped_column(String(30), default="rascunho", index=True)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    items: Mapped[list["VJAdminOrderItem"]] = relationship(
        back_populates="pedido",
        cascade="all, delete-orphan",
        order_by="VJAdminOrderItem.id",
    )
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    updated_by: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_id])
    customer: Mapped["Customer | None"] = relationship("Customer", back_populates="orders")

    def to_dict(self):
        return {
            "id": self.id,
            "customer_id": self.customer_id,
            "cliente_nome": self.cliente_nome,
            "cliente_whatsapp": self.cliente_whatsapp,
            "forma_pagamento": self.forma_pagamento,
            "parcelas": self.parcelas,
            "desconto_total": decimal_to_float(self.desconto_total),
            "subtotal": decimal_to_float(self.subtotal),
            "taxa_pagamento": decimal_to_float(self.taxa_pagamento),
            "total": decimal_to_float(self.total),
            "lucro_estimado": decimal_to_float(self.lucro_estimado),
            "margem_estimada": decimal_to_float(self.margem_estimada),
            "status": self.status,
            "created_by_id": self.created_by_id,
            "updated_by_id": self.updated_by_id,
            "created_by": self.created_by.to_dict() if self.created_by else None,
            "updated_by": self.updated_by.to_dict() if self.updated_by else None,
            "customer": self.customer.to_dict() if self.customer else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "items": [item.to_dict() for item in self.items],
        }


class VJAdminOrderItem(Base):
    __tablename__ = "vj_admin_pedido_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    pedido_id: Mapped[int] = mapped_column(ForeignKey("vj_admin_pedidos.id"), index=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantidade: Mapped[int] = mapped_column(Integer)
    preco_unitario: Mapped[Decimal] = mapped_column(MONEY_COLUMN)
    custo_unitario: Mapped[Decimal] = mapped_column(MONEY_COLUMN)
    taxa_percentual: Mapped[Decimal] = mapped_column(PERCENT_COLUMN, default=Decimal("0.00"))
    lucro_unitario: Mapped[Decimal] = mapped_column(MONEY_COLUMN)
    total_item: Mapped[Decimal] = mapped_column(MONEY_COLUMN)
    pedido: Mapped[VJAdminOrder] = relationship(back_populates="items")
    produto: Mapped[Product] = relationship("Product")

    def to_dict(self):
        product_data = None
        if self.produto:
            product_data = {
                "id": self.produto.id,
                "codigo": self.produto.codigo,
                "nome": self.produto.name,
                "categoria": self.produto.category,
                "saldo_estoque": self.produto.stock_quantity or 0,
            }
        return {
            "id": self.id,
            "pedido_id": self.pedido_id,
            "produto_id": self.produto_id,
            "produto": product_data,
            "quantidade": self.quantidade,
            "preco_unitario": decimal_to_float(self.preco_unitario),
            "custo_unitario": decimal_to_float(self.custo_unitario),
            "taxa_percentual": decimal_to_float(self.taxa_percentual),
            "lucro_unitario": decimal_to_float(self.lucro_unitario),
            "total_item": decimal_to_float(self.total_item),
        }
