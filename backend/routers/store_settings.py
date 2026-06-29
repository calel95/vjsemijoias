from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.database import get_db
from backend.models import User
from backend.services.admin_security import record_admin_audit
from backend.services.email import OutgoingEmail, current_email_config, send_email
from backend.services.validation import normalize_email
from backend.store_config import admin_store_config, update_store_settings


router = APIRouter(prefix="/api/admin/store-config", tags=["Admin - Store Config"])


@router.get("")
def get_admin_store_config(
    _claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    return admin_store_config(db)


@router.put("")
def update_admin_store_config(
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    previous_values = admin_store_config(db).get("values", {})
    try:
        result = update_store_settings(db, data.get("values", data))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    current_values = result.get("values", {})
    changed_keys = [
        key for key, value in current_values.items()
        if str(previous_values.get(key, "")) != str(value)
    ]
    sensitive_keys = [
        key for key in changed_keys
        if key.startswith("SHIPPING_") or key.startswith("COUPON") or key.startswith("EMAIL_")
    ]
    actor = db.get(User, int(claims["sub"])) if claims and claims.get("sub") else None
    record_admin_audit(
        db,
        request,
        "store.config.updated",
        admin_user=actor,
        resource="store_config",
        metadata={
            "changed_keys": changed_keys,
            "sensitive_keys": sensitive_keys,
        },
    )
    db.commit()
    return result

@router.post("/email-test")
def send_admin_email_test(
    request: Request,
    data: dict[str, Any] = Body(default_factory=dict),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    actor = db.get(User, int(claims["sub"])) if claims and claims.get("sub") else None
    try:
        recipient = normalize_email(data.get("email") or (actor.email if actor else ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    email_config = current_email_config()
    sent = send_email(
        OutgoingEmail(
            to=recipient,
            subject="Teste de e-mail - VJ Semijoias",
            text=(
                "Este e-mail confirma que os e-mails transacionais da VJ Semijoias "
                "estao configurados para envio."
            ),
        )
    )
    record_admin_audit(
        db,
        request,
        "store.email.test_sent",
        admin_user=actor,
        resource="store_config",
        metadata={"to": recipient, "backend": email_config.backend, "sent": sent},
    )
    db.commit()
    if not sent:
        raise HTTPException(status_code=400, detail="Nao foi possivel enviar o e-mail de teste")
    return {"message": f"E-mail de teste enviado para {recipient}"}