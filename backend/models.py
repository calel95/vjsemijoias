import json
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


MONEY_COLUMN = Numeric(12, 2)
PERCENT_COLUMN = Numeric(5, 2)


def utc_now():
    return datetime.now(UTC)


def decimal_to_float(value):
    if value is None:
        return None
    return float(value)


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(50))
    categoryName: Mapped[str] = mapped_column(String(50))
    price: Mapped[Decimal] = mapped_column(MONEY_COLUMN)
    oldPrice: Mapped[Decimal | None] = mapped_column(MONEY_COLUMN, nullable=True)
    sku: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    image: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)
    badge: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    stock_status: Mapped[str] = mapped_column(String(30), default="available")
    stock_quantity: Mapped[int] = mapped_column(Integer, default=0)
    low_stock_alert: Mapped[int] = mapped_column(Integer, default=1)
    description: Mapped[str] = mapped_column(Text)
    features: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    gallery_images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.position",
    )
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
            "category": self.category,
            "categoryName": self.categoryName,
            "price": decimal_to_float(self.price),
            "oldPrice": decimal_to_float(self.oldPrice),
            "sku": self.sku,
            "image": self.image,
            "images": images,
            "icon": self.icon or "💎",
            "badge": self.badge,
            "is_active": self.is_active,
            "stock_status": self.stock_status or "available",
            "stock_quantity": self.stock_quantity or 0,
            "low_stock_alert": self.low_stock_alert or 0,
            "stock_is_low": (
                (self.stock_quantity or 0) <= (self.low_stock_alert or 0)
                and (self.stock_status or "available") != "out_of_stock"
            ),
            "description": self.description,
            "features": features,
            "custom": self.custom,
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


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    password_hash: Mapped[str] = mapped_column(String(200))
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
    discount: Mapped[Decimal] = mapped_column(MONEY_COLUMN, default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(MONEY_COLUMN)
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    coupon: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stock_deducted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    payment: Mapped["Payment | None"] = relationship(back_populates="order", uselist=False)

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
            "discount": decimal_to_float(self.discount),
            "total": decimal_to_float(self.total),
            "payment_method": self.payment_method,
            "status": self.status,
            "coupon": self.coupon,
            "stock_deducted": self.stock_deducted,
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    usage_limit: Mapped[int] = mapped_column(Integer, default=100)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class StoreSetting(Base):
    __tablename__ = "store_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
