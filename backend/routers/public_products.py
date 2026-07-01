from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Product
from backend.services.common import get_or_404


router = APIRouter(prefix="/api")
CATEGORY_ICONS = {
    "all": "\U0001F48E",
    "brincos": "\u2728",
    "colares": "\U0001F4FF",
    "pulseiras": "\u269C\ufe0f",
    "aneis": "\U0001F48D",
    "pingentes": "\U0001F52E",
    "chaveiros": "\U0001F511",
    "conjuntos": "\U0001F381",
}


def public_product_filters(category: str = "all", search: str = ""):
    filters = [
        Product.is_active.is_(True),
        Product.publicado.is_(True),
        Product.status.in_(["publicado", "ativo"]),
    ]
    if category and category != "all":
        filters.append(Product.category == category)
    search = search.strip()
    if search:
        search_pattern = f"%{search.lower()}%"
        filters.append(
            or_(
                func.lower(Product.name).like(search_pattern),
                func.lower(Product.description).like(search_pattern),
                func.lower(Product.sku).like(search_pattern),
                func.lower(Product.reference).like(search_pattern),
                func.lower(Product.codigo).like(search_pattern),
            )
        )
    return filters


@router.get("/products")
def get_products(
    category: str = "all",
    search: str = "",
    page: int | None = Query(default=None, ge=1),
    per_page: int | None = Query(default=None, ge=1, le=60),
    db: Session = Depends(get_db),
):
    filters = public_product_filters(category=category, search=search)
    statement = select(Product).where(*filters).order_by(Product.id)
    if page is None and per_page is None:
        products = db.scalars(statement).unique().all()
        return [product.to_dict() for product in products]

    current_page = page or 1
    page_size = per_page or 12
    total = db.scalar(select(func.count(Product.id)).where(*filters)) or 0
    products = db.scalars(
        statement.offset((current_page - 1) * page_size).limit(page_size)
    ).unique().all()
    total_pages = (total + page_size - 1) // page_size if total else 0
    return {
        "items": [product.to_dict() for product in products],
        "page": current_page,
        "per_page": page_size,
        "total": total,
        "total_pages": total_pages,
        "has_next": current_page < total_pages,
        "has_previous": current_page > 1 and total_pages > 0,
    }


@router.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = get_or_404(db, Product, product_id)
    if (
        not product.is_active
        or not product.publicado
        or product.status not in {"publicado", "ativo"}
    ):
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    return product.to_dict()


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    rows = db.execute(
        select(
            Product.category.label("id"),
            func.min(Product.categoryName).label("name"),
        )
        .where(
            Product.is_active.is_(True),
            Product.publicado.is_(True),
            Product.status.in_(["publicado", "ativo"]),
        )
        .group_by(Product.category)
        .order_by(func.min(Product.categoryName), Product.category)
    ).all()
    return [{"id": "all", "name": "Todos", "icon": CATEGORY_ICONS["all"]}] + [
        {
            "id": row.id,
            "name": row.name or row.id.capitalize(),
            "icon": CATEGORY_ICONS.get(row.id, CATEGORY_ICONS["all"]),
        }
        for row in rows
        if row.id
    ]