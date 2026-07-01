import json
import secrets
import shutil
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from backend.auth import admin_claims
from backend.config import IMPORT_UPLOAD_ROOT
from backend.database import get_db
from backend.models import User
from backend.services.admin_security import record_admin_audit


router = APIRouter(prefix="/api")
IMPORT_UPLOAD_MAX_FILE_BYTES = 20 * 1024 * 1024
IMPORT_UPLOAD_MAX_TOTAL_BYTES = 250 * 1024 * 1024
IMPORT_UPLOAD_ALLOWED_EXTENSIONS = {".csv", ".json", ".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.post("/products/import-folder")
def import_product_folder(
    request: Request,
    files: list[UploadFile] = File(...),
    claims=Depends(admin_claims),
    db: Session = Depends(get_db),
):
    normalized_files = []
    for uploaded in files:
        raw_name = (uploaded.filename or "").replace("\\", "/").strip("/")
        relative_path = PurePosixPath(raw_name)
        if not raw_name or relative_path.is_absolute() or ".." in relative_path.parts:
            raise HTTPException(
                status_code=400,
                detail=f"Caminho de arquivo invÃ¡lido: {raw_name}",
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
        total_bytes = 0
        for uploaded, relative_path in normalized_files:
            if catalog_prefix != PurePosixPath("."):
                try:
                    relative_path = relative_path.relative_to(catalog_prefix)
                except ValueError:
                    continue
            extension = relative_path.suffix.lower()
            if extension not in IMPORT_UPLOAD_ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de arquivo nao suportado: {relative_path.name}",
                )
            destination = temp_root.joinpath(*relative_path.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            file_size = 0
            with destination.open("wb") as output:
                while chunk := uploaded.file.read(1024 * 1024):
                    file_size += len(chunk)
                    total_bytes += len(chunk)
                    if file_size > IMPORT_UPLOAD_MAX_FILE_BYTES:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Arquivo maior que 20 MB: {relative_path.name}",
                        )
                    if total_bytes > IMPORT_UPLOAD_MAX_TOTAL_BYTES:
                        raise HTTPException(
                            status_code=400,
                            detail="Importacao maior que 250 MB",
                        )
                    output.write(chunk)
        try:
            from backend.import_products import import_catalog

            summary = import_catalog(temp_root)
        except (
            FileNotFoundError,
            KeyError,
            RuntimeError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise HTTPException(status_code=400, detail=f"CatÃ¡logo invÃ¡lido: {exc}") from exc
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    actor = db.get(User, int(claims["sub"])) if claims and claims.get("sub") else None
    record_admin_audit(
        db,
        request,
        "catalog.imported",
        admin_user=actor,
        resource="catalog",
        metadata=summary,
    )
    db.commit()
    return {"message": "CatÃ¡logo importado com sucesso", **summary}