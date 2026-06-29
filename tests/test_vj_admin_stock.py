from tests.helpers import admin_headers, client


def create_stock_product(headers, code, **overrides):
    payload = {
        "codigo": code,
        "nome": f"Produto Estoque {code}",
        "categoria": "brincos",
        "descricao": "Produto para testes de estoque simples.",
        "custo_peca": 35,
        "estoque": 0,
        "publicado": False,
    }
    payload.update(overrides)
    response = client.post("/api/vj-admin/produtos", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def move_stock(headers, product_id, **payload):
    response = client.post(
        f"/api/vj-admin/produtos/{product_id}/estoque/movimentar",
        headers=headers,
        json=payload,
    )
    return response


def test_vj_admin_creates_stock_entry_movement():
    headers = admin_headers()
    product = create_stock_product(headers, "VJ-STOCK-ENTRADA")

    response = move_stock(
        headers,
        product["id"],
        tipo="entrada",
        quantidade=7,
        motivo="Compra fornecedor",
        observacoes="Lote inicial",
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["produto"]["saldo_estoque"] == 7
    assert data["produto"]["stock_status"] == "available"
    assert data["movimentacao"]["tipo"] == "entrada"
    assert data["movimentacao"]["quantidade"] == 7
    assert data["movimentacao"]["saldo_anterior"] == 0
    assert data["movimentacao"]["saldo_atual"] == 7
    assert data["movimentacao"]["delta"] == 7
    assert data["movimentacao"]["created_by_id"] is not None
    assert data["movimentacao"]["created_by"]["email"] == "admin@vjsemijoias.com"


def test_vj_admin_creates_stock_exit_movement():
    headers = admin_headers()
    product = create_stock_product(headers, "VJ-STOCK-SAIDA", estoque=5)

    response = move_stock(
        headers,
        product["id"],
        tipo="saida",
        quantidade=2,
        motivo="Venda manual",
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["produto"]["saldo_estoque"] == 3
    assert data["movimentacao"]["tipo"] == "saida"
    assert data["movimentacao"]["saldo_anterior"] == 5
    assert data["movimentacao"]["saldo_atual"] == 3
    assert data["movimentacao"]["delta"] == -2


def test_vj_admin_blocks_exit_greater_than_available_stock():
    headers = admin_headers()
    product = create_stock_product(headers, "VJ-STOCK-BLOQUEIO", estoque=1)

    response = move_stock(
        headers,
        product["id"],
        tipo="saida",
        quantidade=2,
        motivo="Venda manual",
    )
    after = client.get(f"/api/vj-admin/produtos/{product['id']}/estoque", headers=headers)

    assert response.status_code == 400
    assert "maior" in response.json()["error"].lower()
    assert after.json()["produto"]["saldo_estoque"] == 1
    assert after.json()["movimentacoes"] == []


def test_vj_admin_adjusts_stock_to_final_balance():
    headers = admin_headers()
    product = create_stock_product(headers, "VJ-STOCK-AJUSTE", estoque=8)

    response = move_stock(
        headers,
        product["id"],
        tipo="ajuste",
        quantidade=5,
        motivo="Conferencia fisica",
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["produto"]["saldo_estoque"] == 5
    assert data["movimentacao"]["tipo"] == "ajuste"
    assert data["movimentacao"]["quantidade"] == 5
    assert data["movimentacao"]["saldo_anterior"] == 8
    assert data["movimentacao"]["saldo_atual"] == 5
    assert data["movimentacao"]["delta"] == -3


def test_vj_admin_returns_stock_history_by_product():
    headers = admin_headers()
    product = create_stock_product(headers, "VJ-STOCK-HIST", estoque=2)
    entrada = move_stock(headers, product["id"], tipo="entrada", quantidade=3, motivo="Reposicao")
    saida = move_stock(headers, product["id"], tipo="saida", quantidade=1, motivo="Venda manual")

    history = client.get(f"/api/vj-admin/produtos/{product['id']}/estoque", headers=headers)

    assert entrada.status_code == 201
    assert saida.status_code == 201
    assert history.status_code == 200
    data = history.json()
    assert data["produto"]["saldo_estoque"] == 4
    assert [item["tipo"] for item in data["movimentacoes"]] == ["saida", "entrada"]
    assert [item["motivo"] for item in data["movimentacoes"]] == ["Venda manual", "Reposicao"]


def test_vj_admin_blocks_common_movements_for_inactive_product_but_allows_adjustment():
    headers = admin_headers()
    product = create_stock_product(
        headers,
        "VJ-STOCK-INATIVO",
        estoque=4,
        status="inativo",
        publicado=False,
    )

    entry = move_stock(headers, product["id"], tipo="entrada", quantidade=1, motivo="Compra")
    exit_response = move_stock(headers, product["id"], tipo="saida", quantidade=1, motivo="Baixa")
    adjustment = move_stock(headers, product["id"], tipo="ajuste", quantidade=2, motivo="Ajuste admin")

    assert entry.status_code == 400
    assert exit_response.status_code == 400
    assert "inativo" in entry.json()["error"].lower()
    assert adjustment.status_code == 201, adjustment.text
    assert adjustment.json()["produto"]["saldo_estoque"] == 2


def test_vj_admin_stock_listing_supports_filters():
    headers = admin_headers()
    supplier = client.post(
        "/api/vj-admin/fornecedores",
        headers=headers,
        json={"nome": "Fornecedor Estoque Filtro"},
    ).json()
    included = create_stock_product(
        headers,
        "VJ-STOCK-FILTRO-A",
        nome="Brinco Estoque Filtrado",
        categoria="brincos",
        fornecedor_id=supplier["id"],
        estoque=1,
        status="publicado",
        publicado=True,
    )
    create_stock_product(headers, "VJ-STOCK-FILTRO-B", nome="Colar Estoque Fora", categoria="colares")

    response = client.get(
        f"/api/vj-admin/estoque?produto=filtrado&categoria=brincos&fornecedor_id={supplier['id']}&status=publicado",
        headers=headers,
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [included["id"]]


def test_zero_stock_product_is_not_available_on_public_site():
    headers = admin_headers()
    product = create_stock_product(
        headers,
        "VJ-STOCK-PUBLICO-ZERO",
        estoque=1,
        status="publicado",
        publicado=True,
    )
    moved = move_stock(headers, product["id"], tipo="saida", quantidade=1, motivo="Venda manual")
    public_response = client.get("/api/products?search=VJ-STOCK-PUBLICO-ZERO")

    assert moved.status_code == 201
    assert moved.json()["produto"]["stock_status"] == "out_of_stock"
    assert public_response.status_code == 200
    public_product = next(item for item in public_response.json() if item["codigo"] == "VJ-STOCK-PUBLICO-ZERO")
    assert public_product["stock_quantity"] == 0
    assert public_product["stock_status"] == "out_of_stock"

