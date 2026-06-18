import logging
import secrets

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import FRONTEND_ROOT, settings
from backend.database import Base, SessionLocal, engine
from backend.routers import auth, catalog_pdf, orders, pages, payments, products, store_settings
from backend.services.admin_security import ADMIN_LOGIN_ATTEMPTS
from backend.services.startup import bootstrap_database


logger = logging.getLogger(__name__)


def create_app():
    app = FastAPI(title="VJ Semijoias API", version="1.0.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
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

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc):
        error_id = secrets.token_hex(8)
        logger.exception(
            "Unhandled exception %s on %s %s",
            error_id,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Erro interno no servidor",
                "error_id": error_id,
            },
        )

    app.include_router(pages.router)
    app.include_router(products.router)
    app.include_router(auth.router)
    app.include_router(payments.router)
    app.include_router(orders.router)
    app.include_router(catalog_pdf.router)
    app.include_router(store_settings.router)
    app.mount("/", StaticFiles(directory=FRONTEND_ROOT, html=True), name="frontend")
    return app


bootstrap_database(Base, engine, SessionLocal)
app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
    )
