import json
import re
import secrets
import shutil
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path, PurePosixPath
from typing import Any

import uvicorn
from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from starlette.background import BackgroundTask
from werkzeug.security import check_password_hash, generate_password_hash

from backend.auth import admin_claims, create_access_token, optional_claims, required_claims
from backend.catalog_pdf import (
    CatalogOptions,
    CatalogProduct,
    generate_catalog_pdf,
    split_values,
    title_from_filename,
    value_at,
)
from backend.config import FRONTEND_ROOT, IMPORT_UPLOAD_ROOT, settings
from backend.database import Base, SessionLocal, engine, get_db
from backend.infinitepay_client import InfinitePayClient, InfinitePayError, checkout_token
from backend.models import (
    Coupon,
    Newsletter,
    Order,
    Payment,
    Product,
    ProductImage,
    User,
)


app = FastAPI(title="VJ Semijoias API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, exc):
    errors = exc.errors()
    message = errors[0].get("msg", "Dados inválidos") if errors else "Dados inválidos"
    return JSONResponse(status_code=422, content={"error": message})


def get_or_404(db: Session, model, identifier):
    instance = db.get(model, identifier)
    if instance is None:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return instance


def product_image_list(data):
    images = data.get("images")
    if isinstance(images, list):
        return [str(image).strip() for image in images if str(image).strip()]
    image = data.get("image")
    return [str(image).strip()] if image else []


def replace_product_gallery(product, images):
    product.image = images[0] if images else None
    product.gallery_images.clear()
    for position, image in enumerate(images):
        product.gallery_images.append(ProductImage(path=image, position=position))


def money(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Valor monetário inválido") from exc


def calculate_order(db: Session, items, coupon_code=""):
    if not isinstance(items, list) or not items:
        raise ValueError("O pedido deve conter ao menos um produto")

    product_ids = []
    quantities = {}
    for item in items:
        try:
            product_id = int(item["id"])
            quantity = int(item.get("quantity", 1))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Item do pedido inválido") from exc
        if quantity < 1 or quantity > 20:
            raise ValueError("A quantidade deve estar entre 1 e 20")
        if product_id not in quantities:
            product_ids.append(product_id)
            quantities[product_id] = 0
        quantities[product_id] += quantity

    products = db.scalars(select(Product).where(Product.id.in_(product_ids))).all()
    products_by_id = {product.id: product for product in products}
    if len(products_by_id) != len(product_ids):
        raise ValueError("Um ou mais produtos não estão disponíveis")

    normalized_items = []
    subtotal = Decimal("0.00")
    for product_id in product_ids:
        product = products_by_id[product_id]
        quantity = quantities[product_id]
        unit_price = money(product.price)
        subtotal += unit_price * quantity
        normalized_items.append(
            {
                "id": product.id,
                "name": product.name,
                "price": float(unit_price),
                "quantity": quantity,
                "image": product.image,
                "icon": product.icon,
            }
        )

    shipping = Decimal("0.00")
    coupon_code = str(coupon_code or "").strip().upper()
    discount = Decimal("0.00")
    if coupon_code:
        coupon = db.scalar(
            select(Coupon).where(
                Coupon.code == coupon_code,
                Coupon.is_active.is_(True),
            )
        )
        if not coupon or coupon.used_count >= coupon.usage_limit:
            raise ValueError("Cupom inválido, expirado ou esgotado")
        discount = (subtotal * money(coupon.discount_percent) / Decimal("100")).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

    return {
        "items": normalized_items,
        "subtotal": subtotal,
        "shipping": shipping,
        "discount": discount,
        "total": subtotal + shipping - discount,
        "coupon": coupon_code,
    }


def validate_order_data(db: Session, data):
    for field in ["customer_name", "customer_email", "customer_cpf", "items"]:
        if not data.get(field):
            raise ValueError(f"Campo obrigatório: {field}")
    if "@" not in str(data["customer_email"]):
        raise ValueError("E-mail inválido")
    return calculate_order(db, data["items"], data.get("coupon", ""))


def create_local_order(db: Session, data, totals, payment_method, claims=None):
    order = Order(
        id="VJ" + datetime.now().strftime("%Y%m%d%H%M%S") + secrets.token_hex(2).upper(),
        user_id=int(claims["sub"]) if claims else None,
        customer_name=data["customer_name"],
        customer_email=data["customer_email"],
        customer_cpf=data["customer_cpf"],
        customer_phone=data.get("customer_phone", ""),
        address_zip=data.get("address_zip", ""),
        address_street=data.get("address_street", ""),
        address_number=data.get("address_number", ""),
        address_complement=data.get("address_complement", ""),
        address_neighborhood=data.get("address_neighborhood", ""),
        address_city=data.get("address_city", ""),
        address_state=data.get("address_state", ""),
        items=json.dumps(totals["items"], ensure_ascii=False),
        subtotal=float(totals["subtotal"]),
        shipping=float(totals["shipping"]),
        discount=float(totals["discount"]),
        total=float(totals["total"]),
        payment_method=payment_method,
        status="pending",
        coupon=totals["coupon"],
    )
    db.add(order)
    return order


def infinitepay():
    return InfinitePayClient(settings.infinitepay_handle, settings.infinitepay_api_base)


def public_url(request: Request, path):
    base = settings.public_base_url or str(request.base_url).rstrip("/")
    return f"{base}/{path.lstrip('/')}"


def cents(value):
    return int((money(value) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def update_infinitepay_payment(payment, provider_data):
    if int(provider_data.get("amount") or 0) != cents(payment.order.total):
        raise ValueError("Valor confirmado pela InfinitePay não corresponde ao pedido")
    if not provider_data.get("success") or not provider_data.get("paid"):
        return False
    payment.provider = "infinitepay"
    payment.provider_order_id = (
        provider_data.get("slug")
        or provider_data.get("invoice_slug")
        or payment.provider_order_id
    )
    payment.provider_payment_id = (
        provider_data.get("transaction_nsu") or payment.provider_payment_id
    )
    payment.method = provider_data.get("capture_method") or payment.method
    payment.status = "paid"
    payment.status_detail = "approved"
    payment.order.payment_method = payment.method
    payment.order.status = "paid"
    return True


@app.get("/api/products")
def get_products(
    category: str = "all",
    search: str = "",
    db: Session = Depends(get_db),
):
    statement = select(Product).order_by(Product.id)
    if category and category != "all":
        statement = statement.where(Product.category == category)
    products = db.scalars(statement).unique().all()
    search = search.lower()
    if search:
        products = [
            product
            for product in products
            if search in product.name.lower() or search in product.description.lower()
        ]
    return [product.to_dict() for product in products]


@app.get("/api/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    return get_or_404(db, Product, product_id).to_dict()


@app.post("/api/products", status_code=201)
def create_product(
    data: dict[str, Any] = Body(default_factory=dict),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    if any(not data.get(field) for field in ["name", "category", "price", "description"]):
        raise HTTPException(
            status_code=400,
            detail="Campos obrigatórios: name, category, price, description",
        )
    images = product_image_list(data)
    product = Product(
        name=data["name"],
        category=data["category"],
        categoryName=data.get("categoryName", data["category"].capitalize()),
        price=float(data["price"]),
        oldPrice=float(data["oldPrice"]) if data.get("oldPrice") else None,
        image=images[0] if images else None,
        icon=data.get("icon", "💎"),
        badge=data.get("badge"),
        description=data["description"],
        features=json.dumps(data.get("features", []), ensure_ascii=False),
        custom=True,
    )
    replace_product_gallery(product, images)
    db.add(product)
    db.commit()
    return product.to_dict()


@app.put("/api/products/{product_id}")
def update_product(
    product_id: int,
    data: dict[str, Any] = Body(default_factory=dict),
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    product = get_or_404(db, Product, product_id)
    for field in ["name", "category", "categoryName", "icon", "badge", "description"]:
        if data.get(field) is not None:
            setattr(product, field, data[field])
    if data.get("price") is not None:
        product.price = float(data["price"])
    if "oldPrice" in data:
        product.oldPrice = float(data["oldPrice"]) if data["oldPrice"] else None
    if "images" in data or "image" in data:
        replace_product_gallery(product, product_image_list(data))
    if data.get("features") is not None:
        product.features = json.dumps(data["features"], ensure_ascii=False)
    db.commit()
    return product.to_dict()


@app.delete("/api/products/{product_id}")
def delete_product(
    product_id: int,
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    db.delete(get_or_404(db, Product, product_id))
    db.commit()
    return {"message": "Produto removido com sucesso"}


@app.post("/api/products/import-folder")
def import_product_folder(
    files: list[UploadFile] = File(...),
    _claims=Depends(admin_claims),
):
    normalized_files = []
    for uploaded in files:
        raw_name = (uploaded.filename or "").replace("\\", "/").strip("/")
        relative_path = PurePosixPath(raw_name)
        if not raw_name or relative_path.is_absolute() or ".." in relative_path.parts:
            raise HTTPException(
                status_code=400,
                detail=f"Caminho de arquivo inválido: {raw_name}",
            )
        normalized_files.append((uploaded, relative_path))

    manifests = [path for _, path in normalized_files if path.name == "manifest.json"]
    if len(manifests) != 1:
        raise HTTPException(
            status_code=400,
            detail="A pasta deve conter exatamente um arquivo manifest.json",
        )
    catalog_prefix = manifests[0].parent
    IMPORT_UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    temp_root = IMPORT_UPLOAD_ROOT / secrets.token_hex(12)
    temp_root.mkdir()
    try:
        for uploaded, relative_path in normalized_files:
            if catalog_prefix != PurePosixPath("."):
                try:
                    relative_path = relative_path.relative_to(catalog_prefix)
                except ValueError:
                    continue
            destination = temp_root.joinpath(*relative_path.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("wb") as output:
                shutil.copyfileobj(uploaded.file, output)
        try:
            from backend.import_products import import_catalog

            summary = import_catalog(temp_root)
        except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=400, detail=f"Catálogo inválido: {exc}") from exc
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    return {"message": "Catálogo importado com sucesso", **summary}


@app.get("/api/categories")
def get_categories():
    return [
        {"id": "all", "name": "Todos", "icon": "💎"},
        {"id": "brincos", "name": "Brincos", "icon": "✨"},
        {"id": "colares", "name": "Colares", "icon": "📿"},
        {"id": "pulseiras", "name": "Pulseiras", "icon": "⚜️"},
        {"id": "aneis", "name": "Anéis", "icon": "💍"},
        {"id": "pingentes", "name": "Pingentes", "icon": "🔮"},
        {"id": "chaveiros", "name": "Chaveiros", "icon": "🔑"},
        {"id": "conjuntos", "name": "Conjuntos", "icon": "🎁"},
    ]


@app.post("/api/auth/register", status_code=201)
def register(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    if any(not data.get(field) for field in ["name", "email", "password"]):
        raise HTTPException(
            status_code=400,
            detail="Campos obrigatórios: name, email, password",
        )
    if db.scalar(select(User).where(User.email == data["email"])):
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")
    if len(data["password"]) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter no mínimo 6 caracteres")
    user = User(
        name=data["name"],
        email=data["email"],
        password_hash=generate_password_hash(data["password"]),
        cpf=data.get("cpf", ""),
        phone=data.get("phone", ""),
        birthdate=data.get("birthdate", ""),
    )
    db.add(user)
    db.commit()
    return {"token": create_access_token(user), "user": user.to_dict()}


@app.post("/api/auth/login")
def login(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    if not data.get("email") or not data.get("password"):
        raise HTTPException(status_code=400, detail="Preencha e-mail e senha")
    user = db.scalar(select(User).where(User.email == data["email"]))
    if not user or not check_password_hash(user.password_hash, data["password"]):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    return {"token": create_access_token(user), "user": user.to_dict()}


@app.get("/api/auth/me")
def get_me(claims=Depends(required_claims), db: Session = Depends(get_db)):
    return get_or_404(db, User, int(claims["sub"])).to_dict()


@app.post("/api/auth/admin/login")
def admin_login(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    if not settings.admin_password:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_PASSWORD não foi configurada no servidor",
        )
    if data.get("password", "") != settings.admin_password:
        raise HTTPException(status_code=401, detail="Senha administrativa incorreta")
    admin_user = db.scalar(select(User).where(User.is_admin.is_(True)))
    if not admin_user:
        admin_user = User(
            name="Administrador",
            email="admin@vjsemijoias.com",
            password_hash=generate_password_hash(settings.admin_password),
            is_admin=True,
        )
        db.add(admin_user)
        db.commit()
    return {"token": create_access_token(admin_user), "user": admin_user.to_dict()}


@app.get("/api/payments/config")
def payment_config():
    return {
        "provider": "infinitepay",
        "enabled": bool(settings.infinitepay_handle),
        "max_installments": 12,
    }


@app.get("/api/payments/{order_id}/status")
def payment_status(order_id: str, token: str = "", db: Session = Depends(get_db)):
    payment = db.scalar(
        select(Payment).where(
            Payment.order_id == order_id,
            Payment.checkout_token == token,
        )
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    return payment.to_dict()


@app.post("/api/payments/infinitepay/checkout", status_code=201)
def create_infinitepay_checkout(
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(optional_claims),
    db: Session = Depends(get_db),
):
    try:
        totals = validate_order_data(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    order = create_local_order(db, data, totals, "infinitepay_checkout", claims)
    payment = Payment(
        order=order,
        checkout_token=checkout_token(),
        provider="infinitepay",
        method="checkout",
    )
    db.add(payment)
    db.flush()
    payload = {
        "order_nsu": order.id,
        "redirect_url": public_url(request, "checkout.html"),
        "webhook_url": public_url(request, "api/payments/webhook/infinitepay"),
        "items": [
            {
                "quantity": 1,
                "price": cents(totals["total"]),
                "description": f"Pedido {order.id} - VJ Semijoias",
            }
        ],
        "customer": {
            "name": order.customer_name,
            "email": order.customer_email,
            "phone_number": f'+55{"".join(filter(str.isdigit, order.customer_phone or ""))}',
        },
        "address": {
            "cep": "".join(filter(str.isdigit, order.address_zip or "")),
            "street": order.address_street or "",
            "neighborhood": order.address_neighborhood or "",
            "number": order.address_number or "",
            "complement": order.address_complement or "",
        },
    }
    try:
        provider_order = infinitepay().create_link(payload)
        checkout_url = provider_order.get("url")
        if not checkout_url:
            raise InfinitePayError(
                "A InfinitePay não retornou o link de pagamento",
                details=provider_order,
            )
        db.commit()
    except InfinitePayError as exc:
        payment.status = "failed"
        payment.status_detail = str(exc)
        order.status = "failed"
        db.commit()
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": str(exc),
                "order_id": order.id,
                "details": exc.details,
            },
        )
    return {
        "order": order.to_dict(),
        "payment": payment.to_dict(),
        "checkout_url": checkout_url,
    }


@app.post("/api/payments/infinitepay/confirm")
def confirm_infinitepay_payment(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    if any(not data.get(field) for field in ["order_nsu", "transaction_nsu", "slug"]):
        raise HTTPException(status_code=400, detail="Dados de confirmação incompletos")
    payment = db.scalar(
        select(Payment).where(
            Payment.order_id == data["order_nsu"],
            Payment.provider == "infinitepay",
        )
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    try:
        provider_data = infinitepay().check_payment(
            data["order_nsu"], data["transaction_nsu"], data["slug"]
        )
        provider_data.update(
            {
                "transaction_nsu": data["transaction_nsu"],
                "slug": data["slug"],
                "capture_method": data.get("capture_method"),
            }
        )
        update_infinitepay_payment(payment, provider_data)
        db.commit()
    except (InfinitePayError, ValueError) as exc:
        return JSONResponse(
            status_code=getattr(exc, "status_code", 400),
            content={"error": str(exc), "details": getattr(exc, "details", None)},
        )
    return {"order": payment.order.to_dict(), "payment": payment.to_dict()}


@app.post("/api/payments/webhook/infinitepay")
def infinitepay_webhook(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    order_nsu = data.get("order_nsu")
    transaction_nsu = data.get("transaction_nsu")
    slug = data.get("invoice_slug") or data.get("slug")
    if not order_nsu or not transaction_nsu or not slug:
        raise HTTPException(status_code=400, detail="Webhook incompleto")
    payment = db.scalar(
        select(Payment).where(
            Payment.order_id == order_nsu,
            Payment.provider == "infinitepay",
        )
    )
    if not payment:
        raise HTTPException(status_code=404, detail="Pedido não encontrado")
    try:
        provider_data = infinitepay().check_payment(order_nsu, transaction_nsu, slug)
        provider_data.update(
            {
                "transaction_nsu": transaction_nsu,
                "slug": slug,
                "capture_method": data.get("capture_method"),
            }
        )
        update_infinitepay_payment(payment, provider_data)
        db.commit()
    except (InfinitePayError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"received": True}


@app.post("/api/orders", status_code=201)
def create_order(
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(optional_claims),
    db: Session = Depends(get_db),
):
    try:
        totals = validate_order_data(db, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    order = create_local_order(
        db, data, totals, data.get("payment_method", "manual"), claims
    )
    db.commit()
    return order.to_dict()


@app.get("/api/orders")
def get_orders(claims=Depends(required_claims), db: Session = Depends(get_db)):
    statement = select(Order).order_by(Order.created_at.desc())
    if not claims.get("is_admin"):
        statement = statement.where(Order.user_id == int(claims["sub"]))
    return [order.to_dict() for order in db.scalars(statement).all()]


@app.get("/api/orders/{order_id}")
def get_order(
    order_id: str,
    claims=Depends(required_claims),
    db: Session = Depends(get_db),
):
    order = get_or_404(db, Order, order_id)
    if not claims.get("is_admin") and order.user_id != int(claims["sub"]):
        raise HTTPException(status_code=403, detail="Acesso negado")
    return order.to_dict()


@app.post("/api/newsletter")
def subscribe_newsletter(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    email = data.get("email", "")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="E-mail inválido")
    if db.scalar(select(Newsletter).where(Newsletter.email == email)):
        return {
            "message": "E-mail já cadastrado! Use o cupom VJ10 para 10% off",
            "coupon": "VJ10",
        }
    db.add(Newsletter(email=email, coupon="VJ10"))
    db.commit()
    return JSONResponse(
        status_code=201,
        content={
            "message": "E-mail cadastrado! Use o cupom VJ10 e ganhe 10% off",
            "coupon": "VJ10",
        },
    )


@app.post("/api/coupons/validate")
def validate_coupon(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    code = data.get("code", "").upper()
    coupon = db.scalar(
        select(Coupon).where(Coupon.code == code, Coupon.is_active.is_(True))
    )
    if not coupon:
        if code == "VJ10":
            return {
                "valid": True,
                "code": "VJ10",
                "discount_percent": 10,
                "message": "Cupom VJ10 aplicado! 10% de desconto",
            }
        raise HTTPException(status_code=404, detail="Cupom inválido ou expirado")
    if coupon.used_count >= coupon.usage_limit:
        raise HTTPException(status_code=400, detail="Cupom esgotado")
    return {
        "valid": True,
        "code": coupon.code,
        "discount_percent": coupon.discount_percent,
        "message": f"Cupom {coupon.code} aplicado! {coupon.discount_percent:.0f}% de desconto",
    }


@app.post("/api/shipping/calculate")
def calculate_shipping(data: dict[str, Any] = Body(default_factory=dict)):
    return {"shipping": 0, "message": "Frete Gratis!", "estimated_days": "5-10"}


@app.get("/api/admin/stats")
def get_admin_stats(
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    total_revenue = db.scalar(
        select(func.sum(Order.total)).where(Order.status.in_(["paid", "confirmed"]))
    ) or 0
    recent_orders = db.scalars(
        select(Order).order_by(Order.created_at.desc()).limit(5)
    ).all()
    return {
        "total_products": db.scalar(select(func.count(Product.id))),
        "total_orders": db.scalar(select(func.count(Order.id))),
        "total_users": db.scalar(select(func.count(User.id))),
        "total_newsletter": db.scalar(select(func.count(Newsletter.id))),
        "total_revenue": total_revenue,
        "recent_orders": [order.to_dict() for order in recent_orders],
    }


@app.post(
    "/api/admin/catalog-pdf",
    tags=["Admin - Catálogo PDF"],
    summary="Gerar catálogo PDF a partir de imagens",
    description=(
        "Envie as imagens na ordem desejada. Os campos nomes, preços, categorias "
        "e descrições são opcionais e aceitam valores separados por | ou por nova linha."
    ),
    responses={
        200: {
            "description": "Catálogo PDF pronto para download",
            "content": {"application/pdf": {}},
        }
    },
)
def generate_catalog_pdf_endpoint(
    images: list[UploadFile] = File(
        ...,
        description="Imagens dos produtos, na ordem em que aparecerão no catálogo.",
    ),
    names: str = Form(
        "",
        description="Nomes separados por |. Se vazio, o nome será extraído do arquivo.",
    ),
    prices: str = Form("", description="Preços separados por |, na ordem das imagens."),
    categories: str = Form(
        "",
        description="Categorias separadas por |, na ordem das imagens.",
    ),
    descriptions: str = Form(
        "",
        description="Descrições separadas por |, na ordem das imagens.",
    ),
    catalog_title: str = Form("CATÁLOGO VJ SEMIJOIAS"),
    collection: str = Form("Coleção Banhada a Ouro 18k"),
    slogan: str = Form("Brilhe em cada momento"),
    contact: str = Form(
        "www.vjsemijoias.com | Instagram: @vj_semijoias | WhatsApp: (51) 98211-0842"
    ),
    coupon: str = Form("VJ10 = 10% OFF"),
    products_per_page: int = Form(
        6,
        description="Use 4 para cards maiores ou 6 para o layout padrão 2x3.",
    ),
    output_filename: str = Form("catalogo-vj-semijoias.pdf"),
    _claims=Depends(admin_claims),
):
    if not images:
        raise HTTPException(status_code=400, detail="Adicione pelo menos uma imagem")
    if len(images) > 100:
        raise HTTPException(status_code=400, detail="Envie no máximo 100 imagens")
    if products_per_page not in {4, 6}:
        raise HTTPException(
            status_code=400,
            detail="products_per_page deve ser 4 ou 6",
        )

    work_root = IMPORT_UPLOAD_ROOT / "catalog-pdf" / secrets.token_hex(12)
    image_root = work_root / "images"
    image_root.mkdir(parents=True, exist_ok=True)
    name_values = split_values(names)
    price_values = split_values(prices)
    category_values = split_values(categories)
    description_values = split_values(descriptions)
    products = []
    try:
        for index, uploaded in enumerate(images):
            if not (uploaded.content_type or "").startswith("image/"):
                raise HTTPException(
                    status_code=400,
                    detail=f"Arquivo não é uma imagem: {uploaded.filename}",
                )
            extension = Path(uploaded.filename or "").suffix.lower() or ".jpg"
            image_path = image_root / f"{index + 1:03d}{extension}"
            size = 0
            with image_path.open("wb") as output:
                while chunk := uploaded.file.read(1024 * 1024):
                    size += len(chunk)
                    if size > 20 * 1024 * 1024:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Imagem maior que 20 MB: {uploaded.filename}",
                        )
                    output.write(chunk)
            products.append(
                CatalogProduct(
                    title=value_at(
                        name_values,
                        index,
                        title_from_filename(uploaded.filename or ""),
                    ),
                    image_path=image_path,
                    price=value_at(price_values, index),
                    category=value_at(category_values, index, "Semijoias"),
                    description=value_at(description_values, index),
                )
            )

        safe_filename = re.sub(
            r"[^A-Za-z0-9._-]+",
            "-",
            Path(output_filename).name,
        ).strip("-")
        if not safe_filename.lower().endswith(".pdf"):
            safe_filename += ".pdf"
        output_path = work_root / safe_filename
        result = generate_catalog_pdf(
            products,
            output_path,
            CatalogOptions(
                title=catalog_title.strip() or "CATÁLOGO VJ SEMIJOIAS",
                collection=collection.strip() or "Coleção Banhada a Ouro 18k",
                slogan=slogan.strip() or "Brilhe em cada momento",
                contact=contact.strip()
                or (
                    "www.vjsemijoias.com | Instagram: @vj_semijoias | "
                    "WhatsApp: (51) 98211-0842"
                ),
                coupon=coupon.strip() or "VJ10 = 10% OFF",
                products_per_page=products_per_page,
            ),
        )
    except HTTPException:
        shutil.rmtree(work_root, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(work_root, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail=f"Não foi possível gerar o catálogo: {exc}",
        ) from exc

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=safe_filename,
        headers={
            "X-Catalog-Products": str(result["products"]),
            "X-Catalog-Pages": str(result["pages"]),
        },
        background=BackgroundTask(shutil.rmtree, work_root, ignore_errors=True),
    )


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "vj-semijoias-api", "framework": "fastapi"}


FRIENDLY_PAGES = {
    "admin": "admin.html",
    "cadastro": "cadastro.html",
    "carrinho": "carrinho.html",
    "catalogo": "catalogo.html",
    "checkout": "checkout.html",
    "login": "login.html",
    "produto": "produto.html",
    "pdf-visualizar": "pdf-visualizar.html",
}


@app.get("/admin", include_in_schema=False)
@app.get("/cadastro", include_in_schema=False)
@app.get("/carrinho", include_in_schema=False)
@app.get("/catalogo", include_in_schema=False)
@app.get("/checkout", include_in_schema=False)
@app.get("/login", include_in_schema=False)
@app.get("/produto", include_in_schema=False)
@app.get("/pdf-visualizar", include_in_schema=False)
def friendly_page(request: Request):
    page_name = request.url.path.strip("/")
    filename = FRIENDLY_PAGES[page_name]
    return FileResponse(FRONTEND_ROOT / filename)


def seed_products(db: Session):
    if db.scalar(select(Product.id).limit(1)) is not None:
        return
    products = [
        ("Brinco Marguerite", "brincos", "Brincos", 149.90, "images/products/brinco-marguerite.svg"),
        ("Colar Sol Dourado", "colares", "Colares", 199.90, "images/products/colar-sol-dourado.svg"),
        ("Pulseira Corrente Tennis", "pulseiras", "Pulseiras", 179.90, "images/products/pulseira-tennis.svg"),
        ("Anel Luna", "aneis", "Anéis", 129.90, "images/products/anel-luna.svg"),
        ("Pingente Flor de Lis", "pingentes", "Pingentes", 99.90, "images/products/pingente-flor-lis.svg"),
        ("Brinco Argola Crocodilo", "brincos", "Brincos", 159.90, "images/products/brinco-argola-crocodilo.svg"),
        ("Colar Gota de Orvalho", "colares", "Colares", 229.90, "images/products/colar-gota-orvalho.svg"),
        ("Pulseira Elo Coração", "pulseiras", "Pulseiras", 149.90, "images/products/pulseira-elo-coracao.svg"),
        ("Anel Duas Cores", "aneis", "Anéis", 139.90, "images/products/anel-duas-cores.svg"),
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
            icon="💎",
            description=name,
            features="[]",
            custom=False,
        )
        product.gallery_images.append(ProductImage(path=image, position=0))
        db.add(product)
    db.add(Coupon(code="VJ10", discount_percent=10, is_active=True))
    db.commit()


Base.metadata.create_all(engine)
with SessionLocal() as startup_db:
    seed_products(startup_db)

app.mount("/", StaticFiles(directory=FRONTEND_ROOT, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
    )
