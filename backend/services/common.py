from fastapi import HTTPException
from sqlalchemy.orm import Session


def get_or_404(db: Session, model, identifier):
    instance = db.get(model, identifier)
    if instance is None:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return instance


def normalize_bool(value, default=True):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() not in {"0", "false", "no", "off", ""}
    return bool(value)
