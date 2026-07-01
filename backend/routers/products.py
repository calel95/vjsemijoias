"""Compatibility module for product routes.

The concrete route handlers live in smaller domain routers:
`public_products`, `admin_products`, and `product_imports`.
"""

from fastapi import APIRouter

from backend.routers.admin_products import (
    create_product,
    delete_all_products,
    delete_product,
    get_admin_products,
    get_storage_status,
    router as admin_router,
    update_product,
)
from backend.routers.product_imports import (
    IMPORT_UPLOAD_ALLOWED_EXTENSIONS,
    IMPORT_UPLOAD_MAX_FILE_BYTES,
    IMPORT_UPLOAD_MAX_TOTAL_BYTES,
    import_product_folder,
    router as import_router,
)
from backend.routers.public_products import (
    CATEGORY_ICONS,
    get_categories,
    get_product,
    get_products,
    public_product_filters,
    router as public_router,
)
from backend.services.product_payload import normalize_product_payload


router = APIRouter()
router.include_router(public_router)
router.include_router(admin_router)
router.include_router(import_router)


__all__ = [
    "CATEGORY_ICONS",
    "IMPORT_UPLOAD_ALLOWED_EXTENSIONS",
    "IMPORT_UPLOAD_MAX_FILE_BYTES",
    "IMPORT_UPLOAD_MAX_TOTAL_BYTES",
    "create_product",
    "delete_all_products",
    "delete_product",
    "get_admin_products",
    "get_categories",
    "get_product",
    "get_products",
    "get_storage_status",
    "import_product_folder",
    "normalize_product_payload",
    "public_product_filters",
    "router",
    "update_product",
]
