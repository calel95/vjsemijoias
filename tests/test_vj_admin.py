import shutil
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pytest

from sqlalchemy import select

from backend.config import FRONTEND_ROOT
from backend.database import SessionLocal
from backend.models import Product, ProductImage
from backend.services.pricing import PAYMENT_FEES, calculate_pricing
from tests.helpers import TINY_GIF_DATA_URL, admin_headers, client


MONEY = Decimal("0.01")
RATIO = Decimal("0.0001")


def expected_price(custo_total, markup, fee):
    return (custo_total * markup / (Decimal("1") - fee / Decimal("100"))).quantize(
        MONEY,
        rounding=ROUND_HALF_UP,
    )


def test_pricing_formula_uses_defaults_and_card_fees():
    pricing = calculate_pricing(Decimal("100.00"))

    assert pricing["custo_embalagem"] == Decimal("9.34")
    assert pricing["custo_total"] == Decimal("109.34")
    assert pricing["markup"] == Decimal("2.00")
    assert pricing["preco_pix"] == Decimal("218.68")
    assert pricing["lucro_pix"] == Decimal("109.34")
    assert pricing["margem_pix"] == Decimal("0.5000")
    assert pricing["preco_credito_12x"] == Decimal("249.63")


@pytest.mark.parametrize(
    ("label", "markup", "expected_pix"),
    [
        ("markup_baixo", Decimal("1.50"), Decimal("89.01")),
        ("markup_padrao", None, Decimal("118.68")),
        ("markup_alto", Decimal("2.75"), Decimal("163.19")),
    ],
)
def test_pricing_accepts_markup_ranges_per_product(label, markup, expected_pix):
    pricing = calculate_pricing(Decimal("50.00"), markup=markup)

    assert label
    assert pricing["custo_total"] == Decimal("59.34")
    assert pricing["markup"] == (markup or Decimal("2.00"))
    assert pricing["preco_pix"] == expected_pix


@pytest.mark.parametrize("field,fee", PAYMENT_FEES.items())
def test_pricing_calculates_each_payment_price_from_fee(field, fee):
    custo_peca = Decimal("80.00")
    custo_embalagem = Decimal("12.50")
    markup = Decimal("2.30")
    custo_total = Decimal("92.50")

    pricing = calculate_pricing(custo_peca, custo_embalagem, markup)

    assert pricing[field] == expected_price(custo_total, markup, fee)


def test_pricing_calculates_pix_profit_and_margin_from_formula():
    pricing = calculate_pricing(Decimal("73.33"), Decimal("9.34"), Decimal("2.35"))
    pix_price = pricing["preco_pix"]
    custo_total = pricing["custo_total"]
    expected_profit = (pix_price - custo_total).quantize(MONEY, rounding=ROUND_HALF_UP)
    expected_margin = (expected_profit / pix_price).quantize(RATIO, rounding=ROUND_HALF_UP)

    assert custo_total == Decimal("82.67")
    assert pix_price == Decimal("194.27")
    assert pricing["lucro_pix"] == expected_profit
    assert pricing["margem_pix"] == expected_margin


def test_vj_admin_pricing_defaults_endpoint():
    headers = admin_headers()

    response = client.get("/api/vj-admin/pricing/defaults", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["custo_embalagem"] == 9.34
    assert data["markup"] == 2.0
    assert data["taxas"]["preco_pix"] == float(PAYMENT_FEES["preco_pix"])
    assert "preco_credito_12x" in data["campos_calculados"]

def test_vj_admin_can_manage_suppliers():
    headers = admin_headers()
    created = client.post(
        "/api/vj-admin/fornecedores",
        headers=headers,
        json={
            "nome": "Fornecedor Teste VJ",
            "whatsapp": "11999999999",
            "instagram": "@fornecedorvj",
            "site": "https://fornecedor.example.com",
            "observacoes": "Fornecedor de aneis.",
        },
    )
    updated = client.put(
        f"/api/vj-admin/fornecedores/{created.json()['id']}",
        headers=headers,
        json={"whatsapp": "11888888888"},
    )
    listed = client.get("/api/vj-admin/fornecedores", headers=headers)

    assert created.status_code == 201
    assert created.json()["nome"] == "Fornecedor Teste VJ"
    assert updated.status_code == 200
    assert updated.json()["whatsapp"] == "11888888888"
    assert any(item["id"] == created.json()["id"] for item in listed.json())


def test_vj_admin_product_pricing_publication_and_public_filter():
    headers = admin_headers()
    supplier = client.post(
        "/api/vj-admin/fornecedores",
        headers=headers,
        json={"nome": "Fornecedor Produto VJ"},
    ).json()

    created = client.post(
        "/api/vj-admin/produtos",
        headers=headers,
        json={
            "codigo": "VJ-MVP-001",
            "nome": "Anel MVP Precificado",
            "categoria": "aneis",
            "fornecedor_id": supplier["id"],
            "material": "Liga metalica",
            "banho": "Ouro 18k",
            "cor": "Dourado",
            "descricao": "Produto do MVP administrativo.",
            "custo_peca": 50,
            "estoque": 4,
            "preco_pix": 9999,
            "publicado": False,
        },
    )
    hidden = client.get("/api/products?search=VJ-MVP-001")
    product_id = created.json()["id"]
    direct_hidden = client.get(f"/api/products/{product_id}")
    published = client.post(f"/api/vj-admin/produtos/{product_id}/publicar", headers=headers)
    visible = client.get("/api/products?search=VJ-MVP-001")
    updated = client.put(
        f"/api/vj-admin/produtos/{product_id}",
        headers=headers,
        json={
            "custo_peca": 60,
            "custo_embalagem": 10,
            "markup": 2.5,
            "preco_pix": 1,
        },
    )
    stored_after_update = client.get(f"/api/vj-admin/produtos/{product_id}", headers=headers)
    unpublished = client.post(f"/api/vj-admin/produtos/{product_id}/despublicar", headers=headers)
    hidden_again = client.get("/api/products?search=VJ-MVP-001")

    assert created.status_code == 201
    data = created.json()
    assert data["codigo"] == "VJ-MVP-001"
    assert data["fornecedor_id"] == supplier["id"]
    assert data["custo_embalagem"] == 9.34
    assert data["markup"] == 2.0
    assert data["custo_total"] == 59.34
    assert data["preco_pix"] == 118.68
    assert data["preco_pix"] != 9999
    assert data["publicado"] is False
    assert hidden.status_code == 200
    assert not any(item["codigo"] == "VJ-MVP-001" for item in hidden.json())
    assert direct_hidden.status_code == 404
    assert published.status_code == 200
    assert published.json()["publicado"] is True
    assert any(item["codigo"] == "VJ-MVP-001" for item in visible.json())
    assert updated.status_code == 200
    assert updated.json()["custo_total"] == 70.0
    assert updated.json()["preco_pix"] == 175.0
    assert stored_after_update.json()["preco_pix"] == 175.0
    assert unpublished.status_code == 200
    assert unpublished.json()["publicado"] is False
    assert not any(item["codigo"] == "VJ-MVP-001" for item in hidden_again.json())

    with SessionLocal() as db:
        stored = db.get(Product, product_id)
        assert stored.price == Decimal("175.00")
        assert stored.preco_pix == Decimal("175.00")


def test_vj_admin_ignores_manual_updates_to_calculated_fields():
    headers = admin_headers()
    created = client.post(
        "/api/vj-admin/produtos",
        headers=headers,
        json={
            "codigo": "VJ-CALC-PROTEGIDO",
            "nome": "Produto Campo Calculado",
            "categoria": "brincos",
            "descricao": "Produto para validar campos protegidos.",
            "custo_peca": 25,
        },
    )
    product_id = created.json()["id"]
    before = created.json()

    updated = client.put(
        f"/api/vj-admin/produtos/{product_id}",
        headers=headers,
        json={
            "preco_pix": 1,
            "preco_debito": 1,
            "custo_total": 1,
            "lucro_pix": 1,
            "margem_pix": 1,
        },
    )

    assert created.status_code == 201
    assert updated.status_code == 200
    assert updated.json()["custo_total"] == before["custo_total"]
    assert updated.json()["preco_pix"] == before["preco_pix"]
    assert updated.json()["preco_debito"] == before["preco_debito"]
    assert updated.json()["lucro_pix"] == before["lucro_pix"]
    assert updated.json()["margem_pix"] == before["margem_pix"]


def test_vj_admin_routes_require_admin_auth():
    supplier = client.get("/api/vj-admin/fornecedores")
    product = client.post("/api/vj-admin/produtos", json={})

    assert supplier.status_code == 401
    assert product.status_code == 401


def create_vj_product(headers, code, **overrides):
    payload = {
        "codigo": code,
        "nome": f"Produto {code}",
        "categoria": "brincos",
        "descricao": "Produto criado para teste da fase 1.2.",
        "custo_peca": 40,
        "publicado": False,
    }
    payload.update(overrides)
    response = client.post("/api/vj-admin/produtos", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_vj_admin_product_filters_by_search_category_supplier_and_status():
    headers = admin_headers()
    supplier_a = client.post(
        "/api/vj-admin/fornecedores",
        headers=headers,
        json={"nome": "Filtro Fornecedor A"},
    ).json()
    supplier_b = client.post(
        "/api/vj-admin/fornecedores",
        headers=headers,
        json={"nome": "Filtro Fornecedor B"},
    ).json()
    product_a = create_vj_product(
        headers,
        "VJ-FILTRO-A",
        nome="Argola Filtro Especial",
        categoria="brincos",
        fornecedor_id=supplier_a["id"],
        publicado=True,
        status="publicado",
    )
    product_b = create_vj_product(
        headers,
        "VJ-FILTRO-B",
        nome="Colar Filtro Discreto",
        categoria="colares",
        fornecedor_id=supplier_b["id"],
        status="rascunho",
    )

    by_name = client.get("/api/vj-admin/produtos?search=argola", headers=headers).json()
    by_code = client.get("/api/vj-admin/produtos?search=VJ-FILTRO-B", headers=headers).json()
    by_category = client.get("/api/vj-admin/produtos?categoria=brincos", headers=headers).json()
    by_supplier = client.get(
        f"/api/vj-admin/produtos?fornecedor_id={supplier_b['id']}",
        headers=headers,
    ).json()
    by_status = client.get("/api/vj-admin/produtos?status=publicado", headers=headers).json()

    assert any(item["id"] == product_a["id"] for item in by_name)
    assert all("argola" in item["nome"].lower() or "argola" in str(item["codigo"]).lower() for item in by_name)
    assert [item["id"] for item in by_code] == [product_b["id"]]
    assert any(item["id"] == product_a["id"] for item in by_category)
    assert all(item["categoria"] == "brincos" for item in by_category)
    assert [item["id"] for item in by_supplier] == [product_b["id"]]
    assert any(item["id"] == product_a["id"] for item in by_status)
    assert all(item["publicado"] is True for item in by_status)


def test_vj_admin_product_audit_fields_are_recorded_on_create_and_update():
    headers = admin_headers()
    created = create_vj_product(headers, "VJ-AUDIT-001")
    updated = client.put(
        f"/api/vj-admin/produtos/{created['id']}",
        headers=headers,
        json={"nome": "Produto Auditado Editado"},
    )

    assert created["created_by_id"] is not None
    assert created["updated_by_id"] == created["created_by_id"]
    assert created["created_by"]["email"] == "admin@vjsemijoias.com"
    assert updated.status_code == 200
    assert updated.json()["updated_by_id"] == created["created_by_id"]
    assert updated.json()["updated_by"]["email"] == "admin@vjsemijoias.com"


def test_vj_admin_exports_filtered_products_as_csv():
    headers = admin_headers()
    included = create_vj_product(headers, "VJ-CSV-INCLUIDO", nome="Produto CSV Incluido")
    create_vj_product(headers, "VJ-CSV-FORA", nome="Produto CSV Fora")

    response = client.get("/api/vj-admin/produtos/export.csv?search=CSV-INCLUIDO", headers=headers)
    content = response.content.decode("utf-8-sig")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert "codigo,nome,categoria" in content
    assert included["codigo"] in content
    assert "VJ-CSV-FORA" not in content


def test_vj_admin_deactivate_requires_confirmation_and_hides_product_from_site():
    headers = admin_headers()
    product = create_vj_product(
        headers,
        "VJ-INATIVAR-001",
        nome="Produto Para Inativar",
        publicado=True,
        status="publicado",
    )
    public_before = client.get("/api/products?search=VJ-INATIVAR-001")
    rejected = client.post(
        f"/api/vj-admin/produtos/{product['id']}/inativar",
        headers=headers,
        json={"confirm": "errado"},
    )
    accepted = client.post(
        f"/api/vj-admin/produtos/{product['id']}/inativar",
        headers=headers,
        json={"confirm": "INATIVAR"},
    )
    public_after = client.get("/api/products?search=VJ-INATIVAR-001")

    assert any(item["codigo"] == "VJ-INATIVAR-001" for item in public_before.json())
    assert rejected.status_code == 400
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "inativo"
    assert accepted.json()["publicado"] is False
    assert accepted.json()["is_active"] is False
    assert accepted.json()["updated_by_id"] is not None
    assert not any(item["codigo"] == "VJ-INATIVAR-001" for item in public_after.json())


# ---------------------------------------------------------------------------
# Sprint 015 - Upload de imagens no VJ Admin modular
# ---------------------------------------------------------------------------


def test_vj_admin_creates_product_with_manual_url_image():
    headers = admin_headers()
    created = client.post(
        "/api/vj-admin/produtos",
        headers=headers,
        json={
            "codigo": "VJ-IMG-URL-001",
            "nome": "Produto URL Manual",
            "categoria": "brincos",
            "descricao": "Produto com URL manual.",
            "custo_peca": 30,
            "imagem_url": "images/products/anel.svg",
        },
    )

    assert created.status_code == 201
    data = created.json()
    assert data["imagem_url"] == "images/products/anel.svg"
    assert data["image"] == "images/products/anel.svg"
    assert data["images"] == ["images/products/anel.svg"]


def test_vj_admin_creates_product_with_data_url_image():
    headers = admin_headers()
    admin_image_root = FRONTEND_ROOT / "images" / "catalog" / "admin"
    created_folder = None

    try:
        created = client.post(
            "/api/vj-admin/produtos",
            headers=headers,
            json={
                "codigo": "VJ-IMG-UPLOAD-001",
                "nome": "Produto Upload Imagem",
                "categoria": "brincos",
                "descricao": "Produto criado com upload de imagem.",
                "custo_peca": 45,
                "imagem_url": TINY_GIF_DATA_URL,
            },
        )

        assert created.status_code == 201
        data = created.json()
        assert data["image"].startswith("images/catalog/admin/")
        assert data["image"].endswith("/img_1.gif")
        assert not data["image"].startswith("data:image/")
        assert data["imagem_url"] == data["image"]
        assert data["images"] == [data["image"]]
        assert (FRONTEND_ROOT / Path(data["image"])).is_file()

        with SessionLocal() as db:
            product = db.get(Product, data["id"])
            assert product.image.startswith("images/catalog/admin/")
            gallery = product.gallery_images
            assert len(gallery) == 1
            assert isinstance(gallery[0], ProductImage)
            assert gallery[0].path == product.image
            assert gallery[0].position == 0

        created_folder = (FRONTEND_ROOT / Path(data["image"])).parent
    finally:
        if created_folder and created_folder.is_relative_to(admin_image_root):
            shutil.rmtree(created_folder, ignore_errors=True)


def test_vj_admin_updates_product_changing_image():
    headers = admin_headers()
    admin_image_root = FRONTEND_ROOT / "images" / "catalog" / "admin"
    created_folder = None

    try:
        created = client.post(
            "/api/vj-admin/produtos",
            headers=headers,
            json={
                "codigo": "VJ-IMG-EDIT-001",
                "nome": "Produto Editar Imagem",
                "categoria": "brincos",
                "descricao": "Produto para editar imagem.",
                "custo_peca": 50,
                "imagem_url": "images/products/anel.svg",
            },
        )
        product_id = created.json()["id"]
        assert created.json()["image"] == "images/products/anel.svg"

        updated = client.put(
            f"/api/vj-admin/produtos/{product_id}",
            headers=headers,
            json={"imagem_url": TINY_GIF_DATA_URL},
        )

        assert updated.status_code == 200
        data = updated.json()
        assert data["image"].startswith("images/catalog/admin/")
        assert data["image"].endswith("/img_1.gif")
        assert not data["image"].startswith("data:image/")
        assert data["images"] == [data["image"]]

        created_folder = (FRONTEND_ROOT / Path(data["image"])).parent
    finally:
        if created_folder and created_folder.is_relative_to(admin_image_root):
            shutil.rmtree(created_folder, ignore_errors=True)


def test_vj_admin_updates_product_removing_image():
    headers = admin_headers()
    admin_image_root = FRONTEND_ROOT / "images" / "catalog" / "admin"
    created_folder = None

    try:
        created = client.post(
            "/api/vj-admin/produtos",
            headers=headers,
            json={
                "codigo": "VJ-IMG-REMOVE-001",
                "nome": "Produto Remover Imagem",
                "categoria": "brincos",
                "descricao": "Produto para remover imagem.",
                "custo_peca": 35,
                "imagem_url": TINY_GIF_DATA_URL,
            },
        )
        product_id = created.json()["id"]
        assert created.json()["image"].startswith("images/catalog/admin/")
        created_folder = (FRONTEND_ROOT / Path(created.json()["image"])).parent

        updated = client.put(
            f"/api/vj-admin/produtos/{product_id}",
            headers=headers,
            json={"imagem_url": ""},
        )

        assert updated.status_code == 200
        data = updated.json()
        assert data["image"] is None
        assert data["imagem_url"] is None
        assert data["images"] == []

        with SessionLocal() as db:
            product = db.get(Product, product_id)
            assert product.image is None
            assert len(product.gallery_images) == 0
    finally:
        if created_folder and created_folder.is_relative_to(admin_image_root):
            shutil.rmtree(created_folder, ignore_errors=True)


def test_vj_admin_rejects_invalid_image_format():
    headers = admin_headers()
    fake_svg_data_url = "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4="

    response = client.post(
        "/api/vj-admin/produtos",
        headers=headers,
        json={
            "codigo": "VJ-IMG-INVALID-001",
            "nome": "Produto Imagem Invalida",
            "categoria": "brincos",
            "descricao": "Produto com imagem invalida.",
            "custo_peca": 25,
            "imagem_url": fake_svg_data_url,
        },
    )

    assert response.status_code == 400
    assert "nao suportado" in response.json()["error"].lower()


def test_vj_admin_rejects_mismatched_image_type():
    headers = admin_headers()
    fake_png_with_gif = TINY_GIF_DATA_URL.replace("image/gif", "image/png")

    response = client.post(
        "/api/vj-admin/produtos",
        headers=headers,
        json={
            "codigo": "VJ-IMG-MISMATCH-001",
            "nome": "Produto Imagem Falsa",
            "categoria": "brincos",
            "descricao": "Produto com mime divergente.",
            "custo_peca": 25,
            "imagem_url": fake_png_with_gif,
        },
    )

    assert response.status_code == 400
    assert "Tipo de imagem" in response.json()["error"]


def test_vj_admin_image_fields_consistency():
    headers = admin_headers()
    admin_image_root = FRONTEND_ROOT / "images" / "catalog" / "admin"
    created_folder = None

    try:
        created = client.post(
            "/api/vj-admin/produtos",
            headers=headers,
            json={
                "codigo": "VJ-IMG-CONSIST-001",
                "nome": "Produto Consistencia Imagem",
                "categoria": "colares",
                "descricao": "Produto para validar consistencia de campos.",
                "custo_peca": 60,
                "imagem_url": TINY_GIF_DATA_URL,
            },
        )

        assert created.status_code == 201
        data = created.json()
        assert data["image"] == data["imagem_url"]
        assert data["images"] == [data["image"]]
        assert data["image"] is not None
        assert not data["image"].startswith("data:")

        created_folder = (FRONTEND_ROOT / Path(data["image"])).parent
    finally:
        if created_folder and created_folder.is_relative_to(admin_image_root):
            shutil.rmtree(created_folder, ignore_errors=True)


def test_vj_admin_local_storage_does_not_require_r2(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    headers = admin_headers()
    admin_image_root = FRONTEND_ROOT / "images" / "catalog" / "admin"
    created_folder = None

    try:
        created = client.post(
            "/api/vj-admin/produtos",
            headers=headers,
            json={
                "codigo": "VJ-IMG-LOCAL-001",
                "nome": "Produto Storage Local",
                "categoria": "brincos",
                "descricao": "Produto com storage local.",
                "custo_peca": 20,
                "imagem_url": TINY_GIF_DATA_URL,
            },
        )

        assert created.status_code == 201
        data = created.json()
        assert data["image"].startswith("images/catalog/admin/")
        assert (FRONTEND_ROOT / Path(data["image"])).is_file()

        created_folder = (FRONTEND_ROOT / Path(data["image"])).parent
    finally:
        if created_folder and created_folder.is_relative_to(admin_image_root):
            shutil.rmtree(created_folder, ignore_errors=True)


def test_vj_admin_r2_incomplete_returns_safe_error_without_secrets(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "r2")
    monkeypatch.delenv("R2_ACCOUNT_ID", raising=False)
    monkeypatch.delenv("R2_BUCKET", raising=False)
    monkeypatch.delenv("R2_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("R2_SECRET_ACCESS_KEY", raising=False)
    monkeypatch.delenv("R2_PUBLIC_BASE_URL", raising=False)
    headers = admin_headers()

    response = client.post(
        "/api/vj-admin/produtos",
        headers=headers,
        json={
            "codigo": "VJ-IMG-R2-FAIL-001",
            "nome": "Produto R2 Incompleto",
            "categoria": "brincos",
            "descricao": "Produto com R2 incompleto.",
            "custo_peca": 20,
            "imagem_url": TINY_GIF_DATA_URL,
        },
    )

    assert response.status_code == 503
    body = response.json()
    body_text = str(body)
    assert "R2_ACCESS_KEY_ID" not in body_text
    assert "R2_SECRET_ACCESS_KEY" not in body_text
    assert "storage" in body_text.lower() or "indisponivel" in body_text.lower()

    with SessionLocal() as db:
        existing = db.scalar(select(Product).where(Product.codigo == "VJ-IMG-R2-FAIL-001"))
        assert existing is None


def test_vj_admin_update_storage_failure_does_not_corrupt_previous_image(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    headers = admin_headers()
    admin_image_root = FRONTEND_ROOT / "images" / "catalog" / "admin"
    created_folder = None

    try:
        created = client.post(
            "/api/vj-admin/produtos",
            headers=headers,
            json={
                "codigo": "VJ-IMG-EDIT-FAIL-001",
                "nome": "Produto Editar Falha Storage",
                "categoria": "brincos",
                "descricao": "Produto para validar falha de storage na edicao.",
                "custo_peca": 40,
                "imagem_url": TINY_GIF_DATA_URL,
            },
        )
        assert created.status_code == 201
        product_id = created.json()["id"]
        original_image = created.json()["image"]
        assert original_image.startswith("images/catalog/admin/")
        created_folder = (FRONTEND_ROOT / Path(original_image)).parent

        monkeypatch.setenv("STORAGE_BACKEND", "r2")
        monkeypatch.delenv("R2_ACCOUNT_ID", raising=False)
        monkeypatch.delenv("R2_BUCKET", raising=False)
        monkeypatch.delenv("R2_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("R2_SECRET_ACCESS_KEY", raising=False)
        monkeypatch.delenv("R2_PUBLIC_BASE_URL", raising=False)

        failed = client.put(
            f"/api/vj-admin/produtos/{product_id}",
            headers=headers,
            json={"imagem_url": TINY_GIF_DATA_URL},
        )

        assert failed.status_code == 503
        body_text = str(failed.json())
        assert "R2_ACCESS_KEY_ID" not in body_text
        assert "R2_SECRET_ACCESS_KEY" not in body_text

        stored = client.get(f"/api/vj-admin/produtos/{product_id}", headers=headers)
        assert stored.status_code == 200
        assert stored.json()["image"] == original_image
        assert stored.json()["images"] == [original_image]
    finally:
        monkeypatch.setenv("STORAGE_BACKEND", "local")
        if created_folder and created_folder.is_relative_to(admin_image_root):
            shutil.rmtree(created_folder, ignore_errors=True)
