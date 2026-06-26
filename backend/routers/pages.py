from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from sqlalchemy import text

from backend.config import FRONTEND_ROOT
from backend.database import SessionLocal


router = APIRouter()

FRIENDLY_PAGES = {
    "admin": "admin.html",
    "cadastro": "cadastro.html",
    "carrinho": "carrinho.html",
    "catalogo": "catalogo.html",
    "checkout": "checkout.html",
    "login": "login.html",
    "produto": "produto.html",
    "pdf-visualizar": "pdf-visualizar.html",
    "pedido": "pedido.html",
}


@router.get("/api/health")
def health():
    return {"status": "ok", "service": "vj-semijoias-api", "framework": "fastapi"}


@router.get("/api/ready")
def ready():
    with SessionLocal() as db:
        db.execute(text("select 1"))
    return {"status": "ready", "database": "ok"}


@router.get("/admin", include_in_schema=False)
@router.get("/cadastro", include_in_schema=False)
@router.get("/carrinho", include_in_schema=False)
@router.get("/catalogo", include_in_schema=False)
@router.get("/checkout", include_in_schema=False)
@router.get("/login", include_in_schema=False)
@router.get("/produto", include_in_schema=False)
@router.get("/pdf-visualizar", include_in_schema=False)
@router.get("/pedido", include_in_schema=False)
def friendly_page(request: Request):
    page_name = request.url.path.strip("/")
    filename = FRIENDLY_PAGES[page_name]
    return FileResponse(FRONTEND_ROOT / filename)