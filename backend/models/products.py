from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, MONEY_COLUMN, RATIO_COLUMN, decimal_to_float, utc_now


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    categoryName: Mapped[str] = mapped_column(String(50))
    price: Mapped[Decimal] = mapped_column(MONEY_COLUMN)
    oldPrice: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    codigo: Mapped[str | None] = mapped_column(
        String(80), index=True, unique=True, nullable=True
    )
    sku: Mapped[str | None] = mapped_column(String(80), index=True, unique=True, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    fornecedor_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    material: Mapped[str | None] = mapped_column(String(120), nullable=True)
    banho: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cor: Mapped[str | None] = mapped_column(String(80), nullable=True)
    custo_peca: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    custo_embalagem: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("9.34"))
    custo_total: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("9.34"))
    markup: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("2.00"))
    preco_pix: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_debito: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_credito_vista: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_credito_2x: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_credito_3x: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_credito_4x: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_credito_5x: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_credito_6x: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_credito_7x: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_credito_8x: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_credito_9x: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_credito_10x: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_credito_11x: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    preco_credito_12x: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    margem_pix: Mapped[Decimal | None] = mapped_column(RATIO_COLUMN, nullable=True)
    lucro_pix: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    image: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)
    badge: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="rascunho")
    publicado: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    stock_status: Mapped[str] = mapped_column(String(30), default="available")
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_alert: Mapped[int] = mapped_column(Integer, default=1)
    weight_grams: Mapped[int] = mapped_column(Integer, default=100)
    height_cm: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("2.00"))
    width_cm: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("10.00"))
    length_cm: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=Decimal("15.00"))
    shipping_profile: Mapped[str] = mapped_column(String(50), default="default")
    description: Mapped[str] = mapped_column(Text)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom: Mapped[bool] = mapped_column(Boolean, default=False)
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
    gallery_images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.position",
    )
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="StockMovement.created_at.desc()",
    )
    supplier: Mapped[Supplier | None] = relationship(back_populates="products")
    created_by: Mapped["User | None"] = relationship("User", foreign_keys=[created_by_id])
    updated_by: Mapped["User | None"] = relationship("User", foreign_keys=[updated_by_id])
    import_record: Mapped["ProductImport | None"] = relationship(
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        try:
            features = json.loads(self.features) if self.features else []
        except (TypeError, json.JSONDecodeError):
            features = self.features.split("\n") if self.features else []
        images = [item.path for item in self.gallery_images]
        if not images and self.image:
            images = [self.image]
        return {
            "id": self.id,
            "name": self.name,
            "nome": self.name,
            "category": self.category,
            "categoria": self.category,
            "categoryName": self.categoryName,
            "price": decimal_to_float(self.price),
            "oldPrice": decimal_to_float(self.oldPrice),
            "codigo": self.codigo,
            "sku": self.sku,
            "reference": self.reference,
            "fornecedor_id": self.fornecedor_id,
            "fornecedor": self.supplier.to_dict() if self.supplier else None,
            "material": self.material,
            "banho": self.banho,
            "cor": self.cor,
            "custo_peca": decimal_to_float(self.custo_peca),
            "custo_embalagem": decimal_to_float(self.custo_embalagem),
            "custo_total": decimal_to_float(self.custo_total),
            "markup": decimal_to_float(self.markup),
            "preco_pix": decimal_to_float(self.preco_pix),
            "preco_debito": decimal_to_float(self.preco_debito),
            "preco_credito_vista": decimal_to_float(self.preco_credito_vista),
            "preco_credito_2x": decimal_to_float(self.preco_credito_2x),
            "preco_credito_3x": decimal_to_float(self.preco_credito_3x),
            "preco_credito_4x": decimal_to_float(self.preco_credito_4x),
            "preco_credito_5x": decimal_to_float(self.preco_credito_5x),
            "preco_credito_6x": decimal_to_float(self.preco_credito_6x),
            "preco_credito_7x": decimal_to_float(self.preco_credito_7x),
            "preco_credito_8x": decimal_to_float(self.preco_credito_8x),
            "preco_credito_9x": decimal_to_float(self.preco_credito_9x),
            "preco_credito_10x": decimal_to_float(self.preco_credito_10x),
            "preco_credito_11x": decimal_to_float(self.preco_credito_11x),
            "preco_credito_12x": decimal_to_float(self.preco_credito_12x),
            "margem_pix": decimal_to_float(self.margem_pix),
            "lucro_pix": decimal_to_float(self.lucro_pix),
            "image": self.image,
            "imagem_url": self.image,
            "images": images,
            "icon": self.icon or "\U0001F48E",
            "badge": self.badge,
            "status": self.status,
            "publicado": self.publicado,
            "is_active": self.is_active,
            "estoque": self.stock_quantity or 0,
            "saldo_estoque": self.stock_quantity or 0,
            "stock_status": self.stock_status or "available",
            "stock_quantity": self.stock_quantity or 0,
            "low_stock_alert": self.low_stock_alert or 0,
            "weight_grams": self.weight_grams or 100,
            "height_cm": decimal_to_float(self.height_cm) or 2.0,
            "width_cm": decimal_to_float(self.width_cm) or 10.0,
            "length_cm": decimal_to_float(self.length_cm) or 15.0,
            "shipping_profile": self.shipping_profile or "default",
            "stock_is_low": (
                (self.stock_quantity or 0) <= (self.low_stock_alert or 0)
                and (self.stock_status or "available") != "out_of_stock"
            ),
            "description": self.description,
            "descricao": self.description,
            "features": features,
            "custom": self.custom,
            "created_by_id": self.created_by_id,
            "updated_by_id": self.updated_by_id,
            "created_by": self.created_by.to_dict() if self.created_by else None,
            "updated_by": self.updated_by.to_dict() if self.updated_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    path: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer, default=0)
    product: Mapped[Product] = relationship(back_populates="gallery_images")


class ProductImport(Base):
    __tablename__ = "product_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), unique=True)
    source_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_folder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    product: Mapped[Product] = relationship(back_populates="import_record")
