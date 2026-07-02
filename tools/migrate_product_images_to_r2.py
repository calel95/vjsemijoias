from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.config import FRONTEND_ROOT
from backend.database import SessionLocal
from backend.models import Product
from backend.services import storage

IMAGE_ROOT = (FRONTEND_ROOT / "images").resolve()
DEFAULT_REPORT_PATH = None


@dataclass(frozen=True)
class ImageReference:
    field: str
    path: str
    position: int
    gallery_id: int | None = None


@dataclass(frozen=True)
class CandidateResult:
    reference: ImageReference
    status: str
    reason: str
    source_path: str | None = None
    target_key: str | None = None
    target_url: str | None = None


def is_absolute_url(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith("http://") or lowered.startswith("https://")


def is_data_url(value: str) -> bool:
    return value.lower().startswith("data:")


def clean_db_image_path(value: str | None) -> str:
    return str(value or "").strip().replace("\\", "/")


def frontend_relative_image_path(value: str) -> str | None:
    path = clean_db_image_path(value).lstrip("/")
    if not path:
        return None
    if path.startswith("frontend/images/"):
        return path.removeprefix("frontend/")
    if path.startswith("images/"):
        return path
    return None


def resolve_local_image(value: str) -> tuple[Path | None, str | None, str | None]:
    image = clean_db_image_path(value)
    if not image:
        return None, None, "caminho vazio"
    if is_absolute_url(image):
        return None, None, "URL absoluta ignorada"
    if is_data_url(image):
        return None, None, "data URL nao deve ser migrada; corrija o cadastro"

    relative = frontend_relative_image_path(image)
    if not relative:
        return None, None, "caminho fora de frontend/images"

    if ".." in Path(relative).parts:
        return None, None, "path traversal bloqueado"

    physical = (FRONTEND_ROOT / relative).resolve()
    try:
        physical.relative_to(IMAGE_ROOT)
    except ValueError:
        return None, None, "arquivo fora de frontend/images"

    if not physical.is_file():
        return physical, relative, "arquivo local inexistente"

    return physical, relative, None


def safe_filename(value: str) -> str:
    name = Path(value).name.strip().replace(" ", "-")
    clean = "".join(char.lower() if char.isalnum() or char in {"-", "_", "."} else "-" for char in name)
    while "--" in clean:
        clean = clean.replace("--", "-")
    return clean.strip("-.") or "imagem"


def r2_key_for(product_id: int, position: int, relative_path: str) -> str:
    return f"catalog/migrated/{product_id}/{position:02d}-{safe_filename(relative_path)}"


def content_type_for(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


def product_references(product: Product) -> list[ImageReference]:
    references: list[ImageReference] = []
    image = clean_db_image_path(product.image)
    if image:
        references.append(ImageReference(field="Product.image", path=image, position=0))
    for index, item in enumerate(product.gallery_images or []):
        path = clean_db_image_path(item.path)
        if not path:
            continue
        position = item.position if item.position is not None else index
        references.append(
            ImageReference(
                field="ProductImage.path",
                path=path,
                position=position,
                gallery_id=item.id,
            )
        )
    return references


def analyze_reference(product: Product, reference: ImageReference) -> CandidateResult:
    physical, relative, problem = resolve_local_image(reference.path)
    if problem:
        status = "ignorar" if "ignorada" in problem or "vazio" in problem else "erro"
        return CandidateResult(reference=reference, status=status, reason=problem)
    assert physical is not None
    assert relative is not None
    key = r2_key_for(product.id, reference.position, relative)
    return CandidateResult(
        reference=reference,
        status="migrar",
        reason="imagem local valida",
        source_path=physical.as_posix(),
        target_key=key,
        target_url=storage.public_asset_url(key, base_url=storage.storage_status()["r2"]["public_base_url"]),
    )


def products_query(product_id: int | None = None):
    statement = select(Product).options(selectinload(Product.gallery_images)).order_by(Product.id)
    if product_id is not None:
        statement = statement.where(Product.id == product_id)
    return statement


def build_report(
    *,
    mode: str,
    products: list[Product],
    product_results: list[dict[str, Any]],
) -> dict[str, Any]:
    image_items = [item for product in product_results for item in product["imagens"]]
    problems = [
        {
            "product_id": product["product_id"],
            "field": item["field"],
            "path": item["path"],
            "motivo": item["motivo"],
        }
        for product in product_results
        for item in product["imagens"]
        if item["status"] == "erro"
    ]
    migrated_or_planned = [item for item in image_items if item["status"] in {"migrar", "migrado"}]
    ignored = [item for item in image_items if item["status"] == "ignorar"]
    return {
        "modo": mode,
        "total_produtos_analisados": len(products),
        "total_imagens_candidatas": len(image_items),
        "total_migrar_ou_migradas": len(migrated_or_planned),
        "total_ignoradas": len(ignored),
        "total_problemas": len(problems),
        "problemas": problems,
        "produtos": product_results,
    }


def result_item(result: CandidateResult, *, applied: bool = False) -> dict[str, Any]:
    status = "migrado" if applied and result.status == "migrar" else result.status
    return {
        "field": result.reference.field,
        "gallery_id": result.reference.gallery_id,
        "position": result.reference.position,
        "path": result.reference.path,
        "status": status,
        "motivo": result.reason,
        "source_path": result.source_path,
        "target_key": result.target_key,
        "target_url": result.target_url,
    }


def product_report(product: Product, results: list[CandidateResult], *, applied: bool = False) -> dict[str, Any]:
    current_images = [ref.path for ref in product_references(product)]
    replacements = {result.reference.path: result.target_url for result in results if result.target_url}
    planned_images = [replacements.get(path, path) for path in current_images]
    return {
        "product_id": product.id,
        "codigo": product.codigo or product.sku,
        "sku": product.sku,
        "nome": product.name,
        "imagens_atuais": current_images,
        "imagens_novas_previstas": planned_images,
        "imagens": [result_item(result, applied=applied) for result in results],
    }


def write_report(report: dict[str, Any], report_path: str | None) -> None:
    if not report_path:
        return
    path = Path(report_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def assert_apply_allowed(*, yes: bool) -> None:
    if not yes:
        raise RuntimeError("Modo apply exige --yes para confirmar alteracao de banco")
    config = storage.validate_storage_config()
    if config.get("backend") != "r2":
        raise RuntimeError("Modo apply exige STORAGE_BACKEND=r2")


def apply_results(product: Product, results: list[CandidateResult]) -> None:
    uploads_by_path: dict[str, str] = {}
    for result in results:
        if result.status != "migrar":
            continue
        if result.reference.path in uploads_by_path:
            continue
        if not result.source_path or not result.target_key:
            raise RuntimeError(f"Imagem sem origem valida: {result.reference.path}")
        source = Path(result.source_path)
        uploads_by_path[result.reference.path] = storage.store_public_file(
            result.target_key,
            source.read_bytes(),
            content_type_for(source),
        )

    if product.image in uploads_by_path:
        product.image = uploads_by_path[product.image]
    for image in product.gallery_images or []:
        if image.path in uploads_by_path:
            image.path = uploads_by_path[image.path]


def run_migration(
    *,
    db: Session,
    apply: bool = False,
    yes: bool = False,
    limit: int | None = None,
    product_id: int | None = None,
    only_missing: bool = False,
    report_path: str | None = None,
) -> dict[str, Any]:
    if apply:
        assert_apply_allowed(yes=yes)

    statement = products_query(product_id)
    if limit is not None:
        statement = statement.limit(limit)
    products = list(db.scalars(statement).unique().all())
    product_results: list[dict[str, Any]] = []

    try:
        for product in products:
            refs = product_references(product)
            if only_missing:
                refs = [ref for ref in refs if not is_absolute_url(ref.path)]
            analyzed = [analyze_reference(product, ref) for ref in refs]
            product_results.append(product_report(product, analyzed, applied=apply))
            if apply:
                apply_results(product, analyzed)
        if apply:
            db.commit()
    except Exception:
        if apply:
            db.rollback()
        raise

    report = build_report(
        mode="apply" if apply else "dry-run",
        products=products,
        product_results=product_results,
    )
    write_report(report, report_path)
    return report


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migra imagens locais de produto para Cloudflare R2.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Simula a migracao sem upload nem banco.")
    mode.add_argument("--apply", action="store_true", help="Executa upload e atualizacao no banco.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--product-id", type=int, default=None)
    parser.add_argument("--only-missing", action="store_true")
    parser.add_argument("--report-path", default=DEFAULT_REPORT_PATH)
    parser.add_argument("--yes", action="store_true", help="Confirma execucao real com --apply.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    apply = bool(args.apply)
    with SessionLocal() as db:
        report = run_migration(
            db=db,
            apply=apply,
            yes=args.yes,
            limit=args.limit,
            product_id=args.product_id,
            only_missing=args.only_missing,
            report_path=args.report_path,
        )
    print(
        "Modo: {modo} | produtos: {produtos} | imagens: {imagens} | migrar/migradas: {migradas} | problemas: {problemas}".format(
            modo=report["modo"],
            produtos=report["total_produtos_analisados"],
            imagens=report["total_imagens_candidatas"],
            migradas=report["total_migrar_ou_migradas"],
            problemas=report["total_problemas"],
        )
    )
    if args.report_path:
        print(f"Relatorio: {args.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())