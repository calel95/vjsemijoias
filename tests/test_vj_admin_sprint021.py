# Sprint 021 - Gerar variantes automaticamente no upload do VJ Admin modular
# Este arquivo e importado por test_vj_admin.py via pytest.

import shutil
from pathlib import Path

import pytest

from backend.config import FRONTEND_ROOT
from backend.database import SessionLocal
from backend.models import Product
from tests.helpers import TINY_GIF_DATA_URL, admin_headers, client


VARIANTS_ROOT = FRONTEND_ROOT / "images" / "variants"


def admin_gallery_folders(images):
    admin_image_root = FRONTEND_ROOT / "images" / "catalog" / "admin"
    folders = set()
    for image in images:
        if not image or image.startswith("http"):
            continue
        image_path = FRONTEND_ROOT / Path(image)
        if image_path.is_file() and image_path.parent.is_relative_to(admin_image_root):
            folders.add(image_path.parent)
    return folders


def cleanup_admin_gallery_folders(folders):
    admin_image_root = FRONTEND_ROOT / "images" / "catalog" / "admin"
    for folder in folders:
        if folder.is_relative_to(admin_image_root):
            shutil.rmtree(folder, ignore_errors=True)


def cleanup_variant_dirs(variant_dirs):
    for vd in variant_dirs:
        if vd.is_relative_to(VARIANTS_ROOT):
            shutil.rmtree(vd, ignore_errors=True)


def test_vj_admin_upload_generates_variants_automatically(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    headers = admin_headers()
    folders = set()
    variant_dirs = set()

    try:
        created = client.post(
            "/api/vj-admin/produtos",
            headers=headers,
            json={
                "codigo": "VJ-VAR-AUTO-001",
                "nome": "Produto Variante Automatica",
                "categoria": "brincos",
                "descricao": "Produto com geracao automatica de variantes.",
                "custo_peca": 30,
                "imagem_url": TINY_GIF_DATA_URL,
            },
        )

        assert created.status_code == 201, created.text
        data = created.json()
        original_path = data["image"]
        assert original_path.startswith("images/catalog/admin/")
        assert (FRONTEND_ROOT / Path(original_path)).is_file()

        stem = Path(original_path).stem
        parent = Path(original_path).parent
        variant_base = VARIANTS_ROOT / parent.relative_to("images")
        for variant_name in ("thumbnail", "card", "detail"):
            variant_file = variant_base / f"{stem}-{variant_name}.webp"
            if not variant_file.is_file():
                variant_file = variant_base / f"{stem}-{variant_name}.gif"
            assert variant_file.is_file(), f"Variante {variant_name} nao encontrada: {variant_file}"
        variant_dirs.add(variant_base)

        folders = admin_gallery_folders([original_path])
    finally:
        cleanup_admin_gallery_folders(folders)
        cleanup_variant_dirs(variant_dirs)


def test_vj_admin_upload_variants_product_image_points_to_original(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    headers = admin_headers()
    folders = set()
    variant_dirs = set()

    try:
        created = client.post(
            "/api/vj-admin/produtos",
            headers=headers,
            json={
                "codigo": "VJ-VAR-ORIG-001",
                "nome": "Produto Variante Original",
                "categoria": "brincos",
                "descricao": "Produto para validar que image aponta para original.",
                "custo_peca": 25,
                "imagem_url": TINY_GIF_DATA_URL,
            },
        )

        assert created.status_code == 201
        data = created.json()
        assert data["image"].startswith("images/catalog/admin/")
        assert "-thumbnail" not in data["image"]
        assert "-card" not in data["image"]
        assert "-detail" not in data["image"]
        assert data["imagem_url"] == data["image"]
        assert data["images"] == [data["image"]]

        with SessionLocal() as db:
            product = db.get(Product, data["id"])
            assert product.image == data["image"]
            for item in product.gallery_images:
                assert item.path == data["image"]
                assert "-thumbnail" not in item.path
                assert "-card" not in item.path
                assert "-detail" not in item.path

        folders = admin_gallery_folders([data["image"]])
        variant_base = VARIANTS_ROOT / Path(data["image"]).parent.relative_to("images")
        variant_dirs.add(variant_base)
    finally:
        cleanup_admin_gallery_folders(folders)
        cleanup_variant_dirs(variant_dirs)


def test_vj_admin_upload_multiple_images_generates_variants_for_each(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    headers = admin_headers()
    folders = set()
    variant_dirs = set()

    try:
        created = client.post(
            "/api/vj-admin/produtos",
            headers=headers,
            json={
                "codigo": "VJ-VAR-MULTI-001",
                "nome": "Produto Multiplas Variantes",
                "categoria": "aneis",
                "descricao": "Produto com multiplos uploads e variantes.",
                "custo_peca": 50,
                "images": [TINY_GIF_DATA_URL, TINY_GIF_DATA_URL],
            },
        )

        assert created.status_code == 201, created.text
        data = created.json()
        assert len(data["images"]) == 2

        for original_path in data["images"]:
            assert (FRONTEND_ROOT / Path(original_path)).is_file()
            stem = Path(original_path).stem
            parent = Path(original_path).parent
            variant_base = VARIANTS_ROOT / parent.relative_to("images")
            found_variants = 0
            for variant_name in ("thumbnail", "card", "detail"):
                variant_file = variant_base / f"{stem}-{variant_name}.webp"
                if not variant_file.is_file():
                    variant_file = variant_base / f"{stem}-{variant_name}.gif"
                if variant_file.is_file():
                    found_variants += 1
            assert found_variants == 3, f"Esperado 3 variantes para {original_path}, encontrado {found_variants}"
            variant_dirs.add(variant_base)

        folders = admin_gallery_folders(data["images"])
    finally:
        cleanup_admin_gallery_folders(folders)
        cleanup_variant_dirs(variant_dirs)


def test_vj_admin_manual_url_does_not_generate_variants():
    headers = admin_headers()

    created = client.post(
        "/api/vj-admin/produtos",
        headers=headers,
        json={
            "codigo": "VJ-VAR-URL-001",
            "nome": "Produto Variante URL Manual",
            "categoria": "brincos",
            "descricao": "Produto com URL manual sem variantes.",
            "custo_peca": 20,
            "imagem_url": "images/products/anel.svg",
        },
    )

    assert created.status_code == 201
    data = created.json()
    assert data["image"] == "images/products/anel.svg"
    variant_path = VARIANTS_ROOT / "products" / "anel-card.webp"
    assert not variant_path.is_file()


def test_vj_admin_svg_upload_does_not_generate_variants_and_does_not_fail():
    headers = admin_headers()
    svg_data_url = "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4="

    response = client.post(
        "/api/vj-admin/produtos",
        headers=headers,
        json={
            "codigo": "VJ-VAR-SVG-001",
            "nome": "Produto Variante SVG",
            "categoria": "brincos",
            "descricao": "Produto SVG sem variantes.",
            "custo_peca": 15,
            "imagem_url": svg_data_url,
        },
    )

    assert response.status_code == 400
    assert "nao suportado" in response.json()["error"].lower()


def test_vj_admin_variant_failure_does_not_prevent_product_creation(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    headers = admin_headers()
    folders = set()

    try:
        import backend.services.image_variants as iv

        def failing_generate_variants(value, *, apply=False, output_root=None):
            raise RuntimeError("Falha simulada na geracao de variantes")

        monkeypatch.setattr(iv, "generate_variants_for_image", failing_generate_variants)

        created = client.post(
            "/api/vj-admin/produtos",
            headers=headers,
            json={
                "codigo": "VJ-VAR-FAIL-001",
                "nome": "Produto Variante Falha",
                "categoria": "brincos",
                "descricao": "Produto com falha de variante controlada.",
                "custo_peca": 22,
                "imagem_url": TINY_GIF_DATA_URL,
            },
        )

        assert created.status_code == 201, created.text
        data = created.json()
        assert data["image"].startswith("images/catalog/admin/")
        assert (FRONTEND_ROOT / Path(data["image"])).is_file()

        with SessionLocal() as db:
            product = db.get(Product, data["id"])
            assert product.image == data["image"]
            assert len(product.gallery_images) == 1

        folders = admin_gallery_folders([data["image"]])
    finally:
        cleanup_admin_gallery_folders(folders)


def test_vj_admin_upload_does_not_persist_data_url(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    headers = admin_headers()
    folders = set()

    try:
        created = client.post(
            "/api/vj-admin/produtos",
            headers=headers,
            json={
                "codigo": "VJ-VAR-NODATA-001",
                "nome": "Produto Variante Sem Data URL",
                "categoria": "brincos",
                "descricao": "Produto para validar que data URL nao e persistida.",
                "custo_peca": 18,
                "imagem_url": TINY_GIF_DATA_URL,
            },
        )

        assert created.status_code == 201
        data = created.json()
        assert not data["image"].startswith("data:")
        assert not data["imagem_url"].startswith("data:")
        for img in data["images"]:
            assert not img.startswith("data:")

        with SessionLocal() as db:
            product = db.get(Product, data["id"])
            assert not product.image.startswith("data:")
            for item in product.gallery_images:
                assert not item.path.startswith("data:")

        folders = admin_gallery_folders([data["image"]])
    finally:
        cleanup_admin_gallery_folders(folders)