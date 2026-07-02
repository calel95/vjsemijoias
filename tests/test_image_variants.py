from decimal import Decimal
from pathlib import Path
import json
import shutil

import pytest
from PIL import Image

from backend.config import FRONTEND_ROOT
from backend.database import SessionLocal
from backend.models import Product, ProductImage
from backend.services.image_variants import (
    DEFAULT_VARIANTS,
    generate_variants_for_image,
    image_dimensions,
    resolve_source_image_path,
)
from tools import generate_image_variants


SOURCE_ROOT = FRONTEND_ROOT / "images" / "catalog" / "test-variants"
OUTPUT_ROOT = FRONTEND_ROOT / "images" / "variants-test"


def cleanup_variant_files():
    shutil.rmtree(SOURCE_ROOT, ignore_errors=True)
    shutil.rmtree(OUTPUT_ROOT, ignore_errors=True)


def write_raster_image(name="produto.jpg", *, size=(1200, 800), image_format="JPEG"):
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    path = SOURCE_ROOT / name
    mode = "RGBA" if image_format == "PNG" else "RGB"
    color = (180, 120, 80, 255) if mode == "RGBA" else (180, 120, 80)
    Image.new(mode, size, color).save(path, format=image_format)
    return path.relative_to(FRONTEND_ROOT).as_posix()


def write_svg_image(name="produto.svg"):
    SOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    path = SOURCE_ROOT / name
    path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"></svg>', encoding="utf-8")
    return path.relative_to(FRONTEND_ROOT).as_posix()


def make_product(db, code, *, image):
    product = Product(
        name=f"Produto {code}",
        category="brincos",
        categoryName="Brincos",
        price=Decimal("99.90"),
        codigo=code,
        sku=code,
        image=image,
        icon="*",
        status="publicado",
        publicado=True,
        is_active=True,
        stock_status="available",
        stock_quantity=1,
        low_stock_alert=1,
        weight_grams=100,
        height_cm=Decimal("2.00"),
        width_cm=Decimal("10.00"),
        length_cm=Decimal("15.00"),
        shipping_profile="default",
        description="Produto para teste de variantes.",
        features="[]",
        custom=True,
    )
    product.gallery_images.append(ProductImage(path=image, position=0))
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture(autouse=True)
def clean_files():
    cleanup_variant_files()
    yield
    cleanup_variant_files()


def test_image_variants_dry_run_does_not_create_files():
    source = write_raster_image("dry-run.jpg")

    report = generate_image_variants.run(
        image=source,
        output_root=OUTPUT_ROOT,
    )

    assert report["modo"] == "dry-run"
    assert report["total_variantes_planejadas"] == len(DEFAULT_VARIANTS)
    assert not OUTPUT_ROOT.exists()


def test_image_variants_apply_requires_yes():
    source = write_raster_image("requires-yes.jpg")

    with pytest.raises(RuntimeError, match="--yes"):
        generate_image_variants.run(
            apply=True,
            yes=False,
            image=source,
            output_root=OUTPUT_ROOT,
        )


def test_image_variants_apply_preserves_original_and_creates_expected_variants():
    source = write_raster_image("produto.jpg", size=(1200, 800))
    source_path = FRONTEND_ROOT / source
    original_bytes = source_path.read_bytes()

    report = generate_image_variants.run(
        apply=True,
        yes=True,
        image=source,
        output_root=OUTPUT_ROOT,
    )

    assert source_path.read_bytes() == original_bytes
    assert report["total_variantes_geradas"] == len(DEFAULT_VARIANTS)
    variants = {
        variant["name"]: variant
        for variant in report["imagens"][0]["variants"]
        if variant["name"] != "original"
    }
    assert set(variants) == {"thumbnail", "card", "detail"}
    for name, max_width in DEFAULT_VARIANTS.items():
        output = FRONTEND_ROOT / variants[name]["output_path"]
        assert output.is_file()
        width, _ = image_dimensions(output)
        assert width <= max_width


def test_image_variants_apply_is_idempotent():
    source = write_raster_image("idempotente.png", image_format="PNG")

    first = generate_image_variants.run(apply=True, yes=True, image=source, output_root=OUTPUT_ROOT)
    second = generate_image_variants.run(apply=True, yes=True, image=source, output_root=OUTPUT_ROOT)

    assert first["total_variantes_geradas"] == len(DEFAULT_VARIANTS)
    assert second["total_variantes_geradas"] == 0
    assert second["total_variantes_existentes"] == len(DEFAULT_VARIANTS)


def test_image_variants_external_url_is_ignored():
    result = generate_variants_for_image("https://cdn.example.com/produto.jpg", output_root=OUTPUT_ROOT)

    assert result["status"] == "ignorar"
    assert "URL externa" in result["reason"]


def test_image_variants_svg_is_not_applicable():
    source = write_svg_image()

    result = generate_variants_for_image(source, output_root=OUTPUT_ROOT)

    assert result["status"] == "ignorar"
    assert "SVG" in result["reason"]
    assert not OUTPUT_ROOT.exists()


def test_image_variants_missing_file_is_reported():
    missing = "images/catalog/test-variants/missing.jpg"

    result = generate_variants_for_image(missing, output_root=OUTPUT_ROOT)

    assert result["status"] == "erro"
    assert "inexistente" in result["reason"]


def test_image_variants_path_traversal_is_blocked():
    result = resolve_source_image_path("images/catalog/../secret.jpg")

    assert result.status == "erro"
    assert "traversal" in result.reason


def test_image_variants_output_root_cannot_escape_frontend_images(tmp_path):
    source = write_raster_image("escape.jpg")

    with pytest.raises(ValueError, match="output-root"):
        generate_variants_for_image(source, apply=True, output_root=tmp_path)


def test_image_variants_report_json_has_expected_fields(tmp_path):
    source = write_raster_image("report.jpg")
    report_path = tmp_path / "variants-report.json"

    report = generate_image_variants.run(
        image=source,
        output_root=OUTPUT_ROOT,
        report_path=str(report_path),
    )

    loaded = json.loads(report_path.read_text(encoding="utf-8"))
    assert loaded["modo"] == "dry-run"
    assert loaded["total_imagens"] == report["total_imagens"] == 1
    assert loaded["imagens"][0]["image"] == source
    assert "variants" in loaded["imagens"][0]


def test_image_variants_does_not_change_database():
    source = write_raster_image("db.jpg")
    with SessionLocal() as db:
        product = make_product(db, "VJ-VARIANT-DB-001", image=source)
        product_id = product.id
        before_image = product.image
        before_gallery = [item.path for item in product.gallery_images]

        report = generate_image_variants.run(
            apply=True,
            yes=True,
            product_id=product_id,
            output_root=OUTPUT_ROOT,
        )
        db.expire_all()
        stored = db.get(Product, product_id)

        assert report["total_variantes_geradas"] == len(DEFAULT_VARIANTS)
        assert stored.image == before_image
        assert [item.path for item in stored.gallery_images] == before_gallery


def test_image_variants_does_not_call_r2(monkeypatch):
    source = write_raster_image("no-r2.jpg")

    def fail_r2(*args, **kwargs):
        raise AssertionError("R2 nao deve ser chamado na Sprint 018")

    monkeypatch.setattr("backend.services.storage.store_public_file", fail_r2)

    report = generate_image_variants.run(
        apply=True,
        yes=True,
        image=source,
        output_root=OUTPUT_ROOT,
    )

    assert report["total_variantes_geradas"] == len(DEFAULT_VARIANTS)