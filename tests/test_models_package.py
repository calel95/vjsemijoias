import backend.models as models
from backend.database import Base


def test_models_package_reexports_public_models():
    expected_names = [
        "AdminAuditLog",
        "Coupon",
        "CouponRedemption",
        "Newsletter",
        "Order",
        "OrderEvent",
        "Payment",
        "Product",
        "ProductImage",
        "ProductImport",
        "StockMovement",
        "StoreSetting",
        "Supplier",
        "User",
        "VJAdminOrder",
        "VJAdminOrderItem",
        "utc_now",
    ]

    for name in expected_names:
        assert hasattr(models, name)


def test_models_package_registers_existing_tables_for_alembic():
    expected_tables = {
        "admin_audit_logs",
        "coupon_redemptions",
        "coupons",
        "newsletters",
        "order_events",
        "orders",
        "payments",
        "product_images",
        "product_imports",
        "products",
        "stock_movements",
        "store_settings",
        "suppliers",
        "users",
        "vj_admin_pedido_items",
        "vj_admin_pedidos",
    }

    assert expected_tables <= set(Base.metadata.tables)
