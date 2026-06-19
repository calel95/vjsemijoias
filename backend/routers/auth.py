import secrets
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from backend.auth import (
    admin_claims,
    create_access_token,
    create_admin_access_token,
    required_claims,
)
from backend.config import settings
from backend.database import get_db
from backend.models import AdminAuditLog, User
from backend.services.admin_security import (
    check_admin_login_rate_limit,
    clear_admin_login_failures,
    record_admin_audit,
    record_admin_login_failure,
)
from backend.services.common import get_or_404


router = APIRouter(prefix="/api/auth")
DEFAULT_ADMIN_EMAIL = "admin@vjsemijoias.com"


def normalize_email(value):
    return str(value or "").strip().lower()


def has_admin_user(db: Session):
    return db.scalar(select(User.id).where(User.is_admin.is_(True)).limit(1)) is not None


def create_bootstrap_admin(db: Session, email: str, password: str):
    existing_user = db.scalar(select(User).where(User.email == (email or DEFAULT_ADMIN_EMAIL)))
    if existing_user:
        existing_user.password_hash = generate_password_hash(password)
        existing_user.is_admin = True
        db.flush()
        return existing_user

    admin_user = User(
        name="Administrador",
        email=email or DEFAULT_ADMIN_EMAIL,
        password_hash=generate_password_hash(password),
        is_admin=True,
    )
    db.add(admin_user)
    db.flush()
    return admin_user


def fail_admin_login(db: Session, request: Request, email: str, message: str):
    record_admin_login_failure(request)
    record_admin_audit(
        db,
        request,
        "admin.login.failed",
        resource="auth",
        metadata={"email": email or None},
    )
    db.commit()
    raise HTTPException(status_code=401, detail=message)


@router.post("/register", status_code=201)
def register(
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    if any(not data.get(field) for field in ["name", "email", "password"]):
        raise HTTPException(
            status_code=400,
            detail="Campos obrigatorios: name, email, password",
        )
    email = normalize_email(data["email"])
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="E-mail ja cadastrado")
    if len(data["password"]) < 6:
        raise HTTPException(status_code=400, detail="A senha deve ter no minimo 6 caracteres")
    user = User(
        name=data["name"],
        email=email,
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
    user = db.scalar(select(User).where(User.email == normalize_email(data["email"])))
    if not user or not check_password_hash(user.password_hash, data["password"]):
        raise HTTPException(status_code=401, detail="E-mail ou senha incorretos")
    return {"token": create_access_token(user), "user": user.to_dict()}


@router.get("/me")
def get_me(claims=Depends(required_claims), db: Session = Depends(get_db)):
    return get_or_404(db, User, int(claims["sub"])).to_dict()


@router.post("/admin/login")
def admin_login(
    request: Request,
    response: Response,
    data: dict[str, Any] = Body(default_factory=dict),
    db: Session = Depends(get_db),
):
    check_admin_login_rate_limit(request)
    password = str(data.get("password", ""))
    email = normalize_email(data.get("email"))
    if not password:
        raise HTTPException(status_code=400, detail="Informe a senha administrativa")

    if not settings.admin_password and not has_admin_user(db):
        raise HTTPException(
            status_code=503,
            detail="Nenhum administrador foi configurado no servidor",
        )

    admin_user = None
    login_mode = "user"
    if email:
        user = db.scalar(select(User).where(User.email == email))
        if user and user.is_admin and check_password_hash(user.password_hash, password):
            admin_user = user
        elif not has_admin_user(db) and secrets.compare_digest(password, settings.admin_password):
            admin_user = create_bootstrap_admin(db, email, password)
            login_mode = "bootstrap"
        else:
            fail_admin_login(db, request, email, "E-mail ou senha administrativa incorretos")
    elif not has_admin_user(db) and secrets.compare_digest(password, settings.admin_password):
        admin_user = create_bootstrap_admin(db, DEFAULT_ADMIN_EMAIL, password)
        login_mode = "bootstrap_legacy"
    else:
        fail_admin_login(db, request, email, "Informe e-mail e senha de administrador")

    clear_admin_login_failures(request)
    record_admin_audit(
        db,
        request,
        "admin.login.succeeded",
        admin_user=admin_user,
        resource="auth",
        metadata={"email": admin_user.email, "mode": login_mode},
    )
    db.commit()
    token = create_admin_access_token(admin_user)
    response.set_cookie(
        key=settings.admin_cookie_name,
        value=token,
        max_age=settings.admin_token_expire_minutes * 60,
        httponly=True,
        secure=settings.admin_cookie_secure,
        samesite=settings.admin_cookie_samesite,
        path="/",
    )
    return {
        "token": token,
        "token_type": "admin",
        "expires_in": settings.admin_token_expire_minutes * 60,
        "user": admin_user.to_dict(),
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(
        key=settings.admin_cookie_name,
        path="/",
        secure=settings.admin_cookie_secure,
        httponly=True,
        samesite=settings.admin_cookie_samesite,
    )
    return {"message": "Sessao encerrada"}


@router.post("/admin/users", status_code=201)
def create_admin_user(
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    email = normalize_email(data.get("email"))
    password = str(data.get("password", ""))
    name = str(data.get("name") or email).strip()
    if not email or not password:
        raise HTTPException(status_code=400, detail="Campos obrigatorios: email, password")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="A senha deve ter no minimo 8 caracteres")
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="E-mail ja cadastrado")

    admin_user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        is_admin=True,
    )
    db.add(admin_user)
    db.flush()
    actor = db.get(User, int(claims["sub"]))
    record_admin_audit(
        db,
        request,
        "admin.user.created",
        admin_user=actor,
        resource="user",
        resource_id=str(admin_user.id),
        metadata={"email": admin_user.email},
    )
    db.commit()
    return {
        "user": admin_user.to_dict(),
    }


@router.get("/admin/audit-logs")
def list_admin_audit_logs(
    limit: int = 50,
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    safe_limit = max(1, min(limit, 200))
    logs = db.scalars(
        select(AdminAuditLog)
        .order_by(AdminAuditLog.created_at.desc(), AdminAuditLog.id.desc())
        .limit(safe_limit)
    ).all()
    return [log.to_dict() for log in logs]
