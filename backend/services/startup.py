from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Product, ProductImage
from backend.store_config import effective_store_settings, sync_coupon_record


def seed_products(db: Session):
    if db.scalar(select(Product.id).limit(1)) is not None:
        return
    products = [
        ("Brinco Marguerite", "brincos", "Brincos", 149.90, "images/products/brinco-marguerite.svg"),
        ("Colar Sol Dourado", "colares", "Colares", 199.90, "images/products/colar-sol-dourado.svg"),
        ("Pulseira Corrente Tennis", "pulseiras", "Pulseiras", 179.90, "images/products/pulseira-tennis.svg"),
        ("Anel Luna", "aneis", "AnÃ©is", 129.90, "images/products/anel-luna.svg"),
        ("Pingente Flor de Lis", "pingentes", "Pingentes", 99.90, "images/products/pingente-flor-lis.svg"),
        ("Brinco Argola Crocodilo", "brincos", "Brincos", 159.90, "images/products/brinco-argola-crocodilo.svg"),
        ("Colar Gota de Orvalho", "colares", "Colares", 229.90, "images/products/colar-gota-orvalho.svg"),
        ("Pulseira Elo CoraÃ§Ã£o", "pulseiras", "Pulseiras", 149.90, "images/products/pulseira-elo-coracao.svg"),
        ("Anel Duas Cores", "aneis", "AnÃ©is", 139.90, "images/products/anel-duas-cores.svg"),
        ("Pingente Estrela", "pingentes", "Pingentes", 109.90, "images/products/pingente-estrela.svg"),
    ]
    for product_id, item in enumerate(products, start=1):
        name, category, category_name, price, image = item
        product = Product(
            id=product_id,
            name=name,
            category=category,
            categoryName=category_name,
            price=price,
            image=image,
            sku=f"SEED-{product_id:03d}",
            stock_quantity=100,
            low_stock_alert=5,
            icon="ðŸ’Ž",
            description=name,
            features="[]",
            status="publicado",
            publicado=True,
            is_active=True,
            preco_pix=price,
            custom=False,
        )
        product.gallery_images.append(ProductImage(path=image, position=0))
        db.add(product)
    db.commit()


def sync_default_coupon(db: Session):
    active_settings = effective_store_settings(db)
    if not active_settings.coupon.code:
        return
    sync_coupon_record(db, active_settings)
    db.commit()


def bootstrap_runtime_data(session_factory):
    with session_factory() as startup_db:
        seed_products(startup_db)
        sync_default_coupon(startup_db)

