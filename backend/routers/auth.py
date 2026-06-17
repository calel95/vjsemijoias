import secrets
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from backend.auth import create_access_token, create_admin_access_token, required_claims
from backend.config import settings
from backend.database import get_db
from backend.models import User
from backend.services.admin_security import (
    check_admin_login_rate_limit,
    clear_admin_login_failures,
    record_admin_login_failure,
)
from backend.services.common import get_or_404


router = APIRouter(prefix="/api/auth")


@router.post("/register", status_code=201)
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


@router.post("/login")
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


@router.get("/me")
def get_me(claims=Depends(required_claims), db: Session = Depends(get_db)):
    return get_or_404(db, User, int(claims["sub"])).to_dict()


@router.post("/admin/login")
def admin_login(
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    check_admin_login_rate_limit(request)
    if not settings.admin_password:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_PASSWORD não foi configurada no servidor",
        )
    if not secrets.compare_digest(str(data.get("password", "")), settings.admin_password):
        record_admin_login_failure(request)
        raise HTTPException(status_code=401, detail="Senha administrativa incorreta")
    clear_admin_login_failures(request)
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
    return {
        "token": create_admin_access_token(admin_user),
        "token_type": "admin",
        "expires_in": settings.admin_token_expire_minutes * 60,
        "user": admin_user.to_dict(),
    }
