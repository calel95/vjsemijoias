from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.database import SessionLocal
from backend.models import Product
from backend.services.image_variants import (
    DEFAULT_OUTPUT_ROOT,
    generate_variants_for_image,
    is_absolute_url,
    write_report,
)
from backend.services.product_media import resolve_product_images


def product_images(product: Product) -> list[str]:
    images = []
    seen = set()
    for image in resolve_product_images(product):
        clean = str(image or "").strip()
        if clean and clean not in seen:
            images.append(clean)
            seen.add(clean)
    return images


def products_query(product_id: int | None = None):
    statement = select(Product).options(selectinload(Product.gallery_images)).order_by(Product.id)
    if product_id is not None:
        statement = statement.where(Product.id == product_id)
    return statement


def collect_candidate_images(*, image: str | None = None, product_id: int | None = None, limit: int | None = None):
    if image:
        return [{"source": "cli", "product_id": None, "codigo": None, "nome": None, "image": image}]

    with SessionLocal() as db:
        statement = products_query(product_id)
        if limit is not None:
            statement = statement.limit(limit)
        products = list(db.scalars(statement).unique().all())
        candidates = []
        for product in products:
            for image_path in product_images(product):
                candidates.append(
                    {
                        "source": "product",
                        "product_id": product.id,
                        "codigo": product.codigo or product.sku,
                        "nome": product.name,
                        "image": image_path,
                    }
                )
        return candidates


def summarize(results: list[dict[str, Any]]) -> dict[str, int]:
    created = sum(
        1
        for result in results
        for variant in result["variants"]
        if variant["status"] == "gerado"
    )
    planned = sum(
        1
        for result in results
        for variant in result["variants"]
        if variant["status"] == "planejado"
    )
    existing = sum(
        1
        for result in results
        for variant in result["variants"]
        if variant["status"] == "existente"
    )
    ignored = sum(1 for result in results if result["status"] == "ignorar")
    errors = sum(1 for result in results if result["status"] == "erro")
    external = sum(1 for result in results if is_absolute_url(result["input"]))
    return {
        "total_imagens": len(results),
        "total_variantes_planejadas": planned,
        "total_variantes_geradas": created,
        "total_variantes_existentes": existing,
        "total_ignoradas": ignored,
        "total_erros": errors,
        "total_urls_externas": external,
    }


def build_report(*, mode: str, candidates: list[dict[str, Any]], results: list[dict[str, Any]], output_root: Path):
    items = []
    for candidate, result in zip(candidates, results):
        items.append({**candidate, **result})
    return {
        "modo": mode,
        "output_root": output_root.as_posix(),
        **summarize(results),
        "imagens": items,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera variantes locais de imagens de produto.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Simula sem criar arquivos.")
    mode.add_argument("--apply", action="store_true", help="Cria arquivos de variantes.")
    parser.add_argument("--image", default=None, help="Imagem local especifica dentro de frontend/images.")
    parser.add_argument("--product-id", type=int, default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--report-path", default=None)
    parser.add_argument("--output-root", default=str(DEFAULT_OUTPUT_ROOT))
    parser.add_argument("--yes", action="store_true", help="Confirma execucao real com --apply.")
    return parser.parse_args(argv)


def run(
    *,
    apply: bool = False,
    yes: bool = False,
    image: str | None = None,
    product_id: int | None = None,
    limit: int | None = None,
    report_path: str | None = None,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
):
    if apply and not yes:
        raise RuntimeError("Modo apply exige --yes para gerar variantes")
    output_root_path = Path(output_root).resolve() if Path(output_root).is_absolute() else (PROJECT_ROOT / output_root).resolve()
    candidates = collect_candidate_images(image=image, product_id=product_id, limit=limit)
    results = [
        generate_variants_for_image(
            candidate["image"],
            apply=apply,
            output_root=output_root_path,
        )
        for candidate in candidates
    ]
    report = build_report(
        mode="apply" if apply else "dry-run",
        candidates=candidates,
        results=results,
        output_root=output_root_path,
    )
    write_report(report, report_path)
    return report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run(
        apply=bool(args.apply),
        yes=args.yes,
        image=args.image,
        product_id=args.product_id,
        limit=args.limit,
        report_path=args.report_path,
        output_root=args.output_root,
    )
    print(
        "Modo: {modo} | imagens: {imagens} | planejadas: {planejadas} | geradas: {geradas} | problemas: {erros}".format(
            modo=report["modo"],
            imagens=report["total_imagens"],
            planejadas=report["total_variantes_planejadas"],
            geradas=report["total_variantes_geradas"],
            erros=report["total_erros"],
        )
    )
    if args.report_path:
        print(f"Relatorio: {args.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())