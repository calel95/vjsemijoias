from decimal import Decimal
from pathlib import Path
import json
import shutil

import pytest

from backend.config import FRONTEND_ROOT
from backend.database import SessionLocal
from backend.models import Product, ProductImage
from tests.helpers import TINY_GIF
from tools import migrate_product_images_to_r2 as migration


TEST_IMAGE_ROOT = FRONTEND_ROOT / "images" / "catalog" / "test-r2-migration"


def configure_r2(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "r2")
    monkeypatch.setenv("R2_ACCOUNT_ID", "account123")
    monkeypatch.setenv("R2_BUCKET", "vjsemijoias-dev")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "access-secret-value")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "super-secret-value")
    monkeypatch.setenv("R2_PUBLIC_BASE_URL", "https://assets-dev.example.com")


def write_test_image(name="img.gif"):
    TEST_IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    path = TEST_IMAGE_ROOT / name
    path.write_bytes(TINY_GIF)
    return path.relative_to(FRONTEND_ROOT).as_posix()


def cleanup_test_images():
    shutil.rmtree(TEST_IMAGE_ROOT, ignore_errors=True)


def make_product(db, code, *, image=None, gallery=None):
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
        description="Produto para teste de migracao.",
        features="[]",
        custom=True,
    )
    for position, path in enumerate(gallery or []):
        product.gallery_images.append(ProductImage(path=path, position=position))
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture(autouse=True)
def clean_storage_env(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    for key in [
        "R2_ACCOUNT_ID",
        "R2_BUCKET",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_PUBLIC_BASE_URL",
    ]:
        monkeypatch.delenv(key, raising=False)
    yield
    cleanup_test_images()


def test_migration_dry_run_does_not_change_database_and_identifies_local_image():
    local_image = write_test_image("dry-run.gif")
    with SessionLocal() as db:
        product = make_product(db, "VJ-R2-DRY-001", image=local_image, gallery=[local_image])
        report = migration.run_migration(db=db, product_id=product.id)
        db.refresh(product)

        assert report["modo"] == "dry-run"
        assert report["total_produtos_analisados"] == 1
        assert report["total_migrar_ou_migradas"] == 2
        assert product.image == local_image
        assert product.gallery_images[0].path == local_image
        assert report["produtos"][0]["imagens"][0]["status"] == "migrar"
        assert report["produtos"][0]["imagens"][0]["target_key"].startswith(
            f"catalog/migrated/{product.id}/"
        )


def test_migration_dry_run_ignores_external_url():
    external = "https://cdn.example.com/produto.jpg"
    with SessionLocal() as db:
        product = make_product(db, "VJ-R2-URL-001", image=external, gallery=[external])
        report = migration.run_migration(db=db, product_id=product.id)

        assert report["total_migrar_ou_migradas"] == 0
        assert report["total_ignoradas"] == 2
        assert all(item["status"] == "ignorar" for item in report["produtos"][0]["imagens"])


def test_migration_dry_run_reports_missing_file():
    missing = "images/catalog/test-r2-migration/missing.gif"
    with SessionLocal() as db:
        product = make_product(db, "VJ-R2-MISSING-001", image=missing, gallery=[missing])
        report = migration.run_migration(db=db, product_id=product.id)

        assert report["total_problemas"] == 2
        assert "inexistente" in report["problemas"][0]["motivo"]


def test_migration_dry_run_blocks_path_traversal():
    traversal = "images/catalog/../secret.gif"
    with SessionLocal() as db:
        product = make_product(db, "VJ-R2-TRAVERSAL-001", image=traversal)
        report = migration.run_migration(db=db, product_id=product.id)

        assert report["total_problemas"] == 1
        assert "traversal" in report["problemas"][0]["motivo"]


def test_migration_apply_requires_r2_backend(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    local_image = write_test_image("requires-r2.gif")
    with SessionLocal() as db:
        product = make_product(db, "VJ-R2-REQ-001", image=local_image)

        with pytest.raises(RuntimeError, match="STORAGE_BACKEND=r2"):
            migration.run_migration(db=db, product_id=product.id, apply=True, yes=True)


def test_migration_apply_requires_yes(monkeypatch):
    configure_r2(monkeypatch)
    local_image = write_test_image("requires-yes.gif")
    with SessionLocal() as db:
        product = make_product(db, "VJ-R2-YES-001", image=local_image)

        with pytest.raises(RuntimeError, match="--yes"):
            migration.run_migration(db=db, product_id=product.id, apply=True, yes=False)


def test_migration_apply_updates_product_and_gallery_preserving_order(monkeypatch):
    configure_r2(monkeypatch)
    first = write_test_image("ordem-1.gif")
    second = write_test_image("ordem-2.gif")
    uploads = []

    def fake_store(key, content, content_type):
        uploads.append((key, content, content_type))
        return f"https://assets-dev.example.com/{key}"

    monkeypatch.setattr(migration.storage, "store_public_file", fake_store)

    with SessionLocal() as db:
        product = make_product(db, "VJ-R2-APPLY-001", image=first, gallery=[first, second])
        report = migration.run_migration(db=db, product_id=product.id, apply=True, yes=True)
        db.refresh(product)

        assert report["modo"] == "apply"
        assert product.image == f"https://assets-dev.example.com/catalog/migrated/{product.id}/00-ordem-1.gif"
        assert [item.path for item in product.gallery_images] == [
            f"https://assets-dev.example.com/catalog/migrated/{product.id}/00-ordem-1.gif",
            f"https://assets-dev.example.com/catalog/migrated/{product.id}/01-ordem-2.gif",
        ]
        assert [item.position for item in product.gallery_images] == [0, 1]
        assert len(uploads) == 2
        assert uploads[0][2] == "image/gif"


def test_migration_apply_is_idempotent_on_second_run(monkeypatch):
    configure_r2(monkeypatch)
    local_image = write_test_image("idempotente.gif")
    uploads = []

    def fake_store(key, content, content_type):
        uploads.append(key)
        return f"https://assets-dev.example.com/{key}"

    monkeypatch.setattr(migration.storage, "store_public_file", fake_store)

    with SessionLocal() as db:
        product = make_product(db, "VJ-R2-IDEMP-001", image=local_image, gallery=[local_image])
        first = migration.run_migration(db=db, product_id=product.id, apply=True, yes=True)
        second = migration.run_migration(db=db, product_id=product.id, apply=True, yes=True)
        db.refresh(product)

        assert first["total_migrar_ou_migradas"] == 2
        assert second["total_migrar_ou_migradas"] == 0
        assert second["total_ignoradas"] == 2
        assert len(uploads) == 1
        assert len(product.gallery_images) == 1


def test_migration_apply_rolls_back_database_when_upload_fails(monkeypatch):
    configure_r2(monkeypatch)
    local_image = write_test_image("rollback.gif")

    def fake_store(key, content, content_type):
        raise RuntimeError("Storage R2 indisponivel")

    monkeypatch.setattr(migration.storage, "store_public_file", fake_store)

    with SessionLocal() as db:
        product = make_product(db, "VJ-R2-ROLLBACK-001", image=local_image, gallery=[local_image])
        product_id = product.id

        with pytest.raises(RuntimeError, match="Storage R2"):
            migration.run_migration(db=db, product_id=product_id, apply=True, yes=True)

    with SessionLocal() as db:
        stored = db.get(Product, product_id)
        assert stored.image == local_image
        assert [item.path for item in stored.gallery_images] == [local_image]


def test_migration_report_json_has_expected_fields_and_no_secrets(monkeypatch, tmp_path):
    configure_r2(monkeypatch)
    local_image = write_test_image("report.gif")
    report_path = tmp_path / "migration-report.json"
    with SessionLocal() as db:
        product = make_product(db, "VJ-R2-REPORT-001", image=local_image, gallery=[local_image])
        report = migration.run_migration(db=db, product_id=product.id, report_path=str(report_path))

    content = report_path.read_text(encoding="utf-8")
    loaded = json.loads(content)
    assert loaded["modo"] == "dry-run"
    assert loaded["total_produtos_analisados"] == report["total_produtos_analisados"]
    assert loaded["produtos"][0]["product_id"] == product.id
    assert "imagens_atuais" in loaded["produtos"][0]
    assert "imagens_novas_previstas" in loaded["produtos"][0]
    assert "access-secret-value" not in content
    assert "super-secret-value" not in content