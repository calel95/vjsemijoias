import json
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


MONEY_COLUMN = Numeric(12, 2)
PERCENT_COLUMN = Numeric(5, 2)
RATIO_COLUMN = Numeric(8, 4)


def utc_now():
    return datetime.now(UTC)


def decimal_to_float(value):
    if value is None:
        return None
    return float(value)


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    whatsapp: Mapped[str | None] = mapped_column(String(30), nullable=True)
    instagram: Mapped[str | None] = mapped_column(String(120), nullable=True)
    site: Mapped[str | None] = mapped_column(String(255), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    products: Mapped[list["Product"]] = relationship(back_populates="supplier")

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "whatsapp": self.whatsapp,
            "instagram": self.instagram,
            "site": self.site,
            "observacoes": self.observacoes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    categoryName: Mapped[str] = mapped_column(String(50))
    price: Mapped[Decimal] = mapped_column(MONEY_COLUMN)
    oldPrice: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    codigo: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
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
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
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


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    produto_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    tipo: Mapped[str] = mapped_column(String(20), index=True)
    quantidade: Mapped[int] = mapped_column(Integer)
    saldo_anterior: Mapped[int] = mapped_column(Integer)
    saldo_atual: Mapped[int] = mapped_column(Integer)
    motivo: Mapped[str] = mapped_column(String(200))
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    product: Mapped[Product] = relationship(back_populates="stock_movements")
    created_by: Mapped["User | None"] = relationship("User")

    def to_dict(self):
        delta = self.saldo_atual - self.saldo_anterior
        return {
            "id": self.id,
            "produto_id": self.produto_id,
            "tipo": self.tipo,
            "quantidade": self.quantidade,
            "delta": delta,
            "saldo_anterior": self.saldo_anterior,
            "saldo_atual": self.saldo_atual,
            "motivo": self.motivo,
            "observacoes": self.observacoes,
            "created_by_id": self.created_by_id,
            "created_by": self.created_by.to_dict() if self.created_by else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class VJAdminOrder(Base):
    __tablename__ = "vj_admin_pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
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
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
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

    def to_dict(self):
        return {
            "id": self.id,
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

class ProductImport(Base):
    __tablename__ = "product_imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), unique=True)
    source_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    source_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_folder: Mapped[str | None] = mapped_column(String(255), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    product: Mapped[Product] = relationship(back_populates="import_record")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
    password_reset_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_reset_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cpf: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    birthdate: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "cpf": self.cpf,
            "phone": self.phone,
            "birthdate": self.birthdate,
            "is_admin": self.is_admin,
        }


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    resource: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    admin_user: Mapped[User | None] = relationship()

    def to_dict(self):
        try:
            metadata = json.loads(self.metadata_json) if self.metadata_json else {}
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return {
            "id": self.id,
            "admin_user_id": self.admin_user_id,
            "action": self.action,
            "resource": self.resource,
            "resource_id": self.resource_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "metadata": metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    customer_name: Mapped[str] = mapped_column(String(200))
    customer_email: Mapped[str] = mapped_column(String(200))
    customer_cpf: Mapped[str] = mapped_column(String(20))
    customer_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_street: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address_complement: Mapped[str | None] = mapped_column(String(200), nullable=True)
    address_neighborhood: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address_state: Mapped[str | None] = mapped_column(String(10), nullable=True)
    items: Mapped[str] = mapped_column(Text)
    subtotal: Mapped[Decimal] = mapped_column(MONEY_COLUMN)
    shipping: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    shipping_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shipping_service: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipping_estimated_days: Mapped[str | None] = mapped_column(String(50), nullable=True)
    shipping_destination_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    shipping_option_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipping_company_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shipping_company: Mapped[str | None] = mapped_column(String(100), nullable=True)
    discount: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(MONEY_COLUMN)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    coupon: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stock_deducted: Mapped[bool] = mapped_column(Boolean, default=False)
    idempotency_key: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    public_token: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    tracking_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tracking_carrier: Mapped[str | None] = mapped_column(String(100), nullable=True)
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    payment: Mapped["Payment | None"] = relationship(back_populates="order", uselist=False)
    events: Mapped[list["OrderEvent"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderEvent.created_at",
    )
    coupon_redemptions: Mapped[list["CouponRedemption"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "customer_name": self.customer_name,
            "customer_email": self.customer_email,
            "customer_cpf": self.customer_cpf,
            "customer_phone": self.customer_phone,
            "address_zip": self.address_zip,
            "address_street": self.address_street,
            "address_number": self.address_number,
            "address_complement": self.address_complement,
            "address_neighborhood": self.address_neighborhood,
            "address_city": self.address_city,
            "address_state": self.address_state,
            "items": json.loads(self.items) if self.items else [],
            "subtotal": decimal_to_float(self.subtotal),
            "shipping": decimal_to_float(self.shipping),
            "shipping_provider": self.shipping_provider,
            "shipping_service": self.shipping_service,
            "shipping_estimated_days": self.shipping_estimated_days,
            "shipping_destination_zip": self.shipping_destination_zip,
            "shipping_option_id": self.shipping_option_id,
            "shipping_company_id": self.shipping_company_id,
            "shipping_company": self.shipping_company,
            "discount": decimal_to_float(self.discount),
            "total": decimal_to_float(self.total),
            "payment_method": self.payment_method,
            "status": self.status,
            "coupon": self.coupon,
            "stock_deducted": self.stock_deducted,
            "public_token": self.public_token,
            "tracking_code": self.tracking_code,
            "tracking_carrier": self.tracking_carrier,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "events": [event.to_dict() for event in self.events],
        }


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    message: Mapped[str] = mapped_column(String(255))
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    order: Mapped[Order] = relationship(back_populates="events")
    actor_user: Mapped[User | None] = relationship()

    def to_dict(self):
        try:
            metadata = json.loads(self.metadata_json) if self.metadata_json else {}
        except (TypeError, json.JSONDecodeError):
            metadata = {}
        return {
            "id": self.id,
            "order_id": self.order_id,
            "event_type": self.event_type,
            "status": self.status,
            "message": self.message,
            "actor_user_id": self.actor_user_id,
            "metadata": metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True)
    provider: Mapped[str] = mapped_column(String(30), default="infinitepay")
    provider_order_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    provider_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checkout_token: Mapped[str] = mapped_column(String(100), unique=True)
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    method: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    status_detail: Mapped[str | None] = mapped_column(String(100), nullable=True)
    pix_qr_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    pix_qr_code_base64: Mapped[str | None] = mapped_column(Text, nullable=True)
    pix_ticket_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    order: Mapped[Order] = relationship(back_populates="payment")

    def to_dict(self, include_pix=True):
        data = {
            "order_id": self.order_id,
            "provider": self.provider,
            "provider_order_id": self.provider_order_id,
            "provider_payment_id": self.provider_payment_id,
            "method": self.method,
            "status": self.status,
            "status_detail": self.status_detail,
            "checkout_token": self.checkout_token,
            "checkout_url": self.checkout_url,
        }
        if include_pix and self.method == "pix":
            data.update(
                {
                    "pix_qr_code": self.pix_qr_code,
                    "pix_qr_code_base64": self.pix_qr_code_base64,
                    "pix_ticket_url": self.pix_ticket_url,
                }
            )
        return data


class Newsletter(Base):
    __tablename__ = "newsletters"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True)
    coupon: Mapped[str] = mapped_column(String(20), default="VJ10")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Coupon(Base):
    __tablename__ = "coupons"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    discount_percent: Mapped[Decimal] = mapped_column(
        PERCENT_COLUMN,
        default=Decimal("10.00"),
    )
    discount_type: Mapped[str] = mapped_column(String(20), default="percent")
    discount_value: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("10.00"))
    minimum_subtotal: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    usage_limit: Mapped[int] = mapped_column(Integer, default=100)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    per_customer_limit: Mapped[int] = mapped_column(Integer, default=0)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    redemptions: Mapped[list["CouponRedemption"]] = relationship(
        back_populates="coupon",
        cascade="all, delete-orphan",
        order_by="CouponRedemption.created_at",
    )

    def to_dict(self, include_redemptions: bool = False):
        data = {
            "id": self.id,
            "code": self.code,
            "discount_percent": decimal_to_float(self.discount_percent),
            "discount_type": self.discount_type,
            "discount_value": decimal_to_float(self.discount_value),
            "minimum_subtotal": decimal_to_float(self.minimum_subtotal),
            "is_active": self.is_active,
            "usage_limit": self.usage_limit,
            "used_count": self.used_count,
            "per_customer_limit": self.per_customer_limit,
            "starts_at": self.starts_at.isoformat() if self.starts_at else None,
            "ends_at": self.ends_at.isoformat() if self.ends_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_redemptions:
            data["redemptions"] = [
                redemption.to_dict()
                for redemption in sorted(
                    self.redemptions,
                    key=lambda item: item.created_at or datetime.min.replace(tzinfo=UTC),
                    reverse=True,
                )[:20]
            ]
        return data


class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.id"), index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("orders.id"), unique=True, index=True)
    customer_email: Mapped[str | None] = mapped_column(String(200), index=True, nullable=True)
    customer_cpf: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    discount_amount: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    coupon: Mapped[Coupon] = relationship(back_populates="redemptions")
    order: Mapped[Order] = relationship(back_populates="coupon_redemptions")

    def to_dict(self):
        return {
            "id": self.id,
            "coupon_id": self.coupon_id,
            "order_id": self.order_id,
            "customer_email": self.customer_email,
            "customer_cpf": self.customer_cpf,
            "discount_amount": decimal_to_float(self.discount_amount),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StoreSetting(Base):
    __tablename__ = "store_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )






