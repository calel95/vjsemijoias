from decimal import Decimal, ROUND_HALF_UP

from backend.database import SessionLocal
from backend.models import Product, VJAdminOrder
from backend.services.vj_orders import cancel_vj_admin_order, confirm_vj_admin_order
from tests.helpers import admin_headers, client


def create_order_product(headers, code, **overrides):
    payload = {
        "codigo": code,
        "nome": f"Produto Pedido {code}",
        "categoria": "brincos",
        "descricao": "Produto para testes de pedido simples.",
        "custo_peca": 50,
        "estoque": 5,
        "status": "publicado",
        "publicado": True,
    }
    payload.update(overrides)
    response = client.post("/api/vj-admin/produtos", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_order(headers, product, **overrides):
    payload = {
        "cliente_nome": "Cliente Pedido",
        "cliente_whatsapp": "11999999999",
        "forma_pagamento": "pix",
        "parcelas": 1,
        "desconto_total": 0,
        "items": [{"produto_id": product["id"], "quantidade": 1}],
    }
    payload.update(overrides)
    response = client.post("/api/vj-admin/pedidos", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_vj_admin_creates_draft_order_without_deducting_stock():
    headers = admin_headers()
    product = create_order_product(headers, "VJ-ORDER-DRAFT", estoque=4)

    order = create_order(headers, product, items=[{"produto_id": product["id"], "quantidade": 2}])
    stock = client.get(f"/api/vj-admin/produtos/{product['id']}/estoque", headers=headers).json()

    assert order["status"] == "rascunho"
    assert order["cliente_nome"] == "Cliente Pedido"
    assert len(order["items"]) == 1
    assert order["items"][0]["quantidade"] == 2
    assert stock["produto"]["saldo_estoque"] == 4
    assert stock["movimentacoes"] == []


def test_vj_admin_confirms_order_and_deducts_stock():
    headers = admin_headers()
    product = create_order_product(headers, "VJ-ORDER-CONFIRM", estoque=5)
    order = create_order(headers, product, items=[{"produto_id": product["id"], "quantidade": 2}])

    confirmed = client.post(f"/api/vj-admin/pedidos/{order['id']}/confirmar", headers=headers)
    stock = client.get(f"/api/vj-admin/produtos/{product['id']}/estoque", headers=headers).json()

    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmado"
    assert stock["produto"]["saldo_estoque"] == 3
    assert stock["movimentacoes"][0]["tipo"] == "saida"
    assert stock["movimentacoes"][0]["quantidade"] == 2
    assert f"#{order['id']}" in stock["movimentacoes"][0]["motivo"]


def test_vj_admin_blocks_order_confirmation_without_stock():
    headers = admin_headers()
    product = create_order_product(headers, "VJ-ORDER-NOSTOCK", estoque=1)
    order = create_order(headers, product, items=[{"produto_id": product["id"], "quantidade": 2}])

    confirmed = client.post(f"/api/vj-admin/pedidos/{order['id']}/confirmar", headers=headers)
    stock = client.get(f"/api/vj-admin/produtos/{product['id']}/estoque", headers=headers).json()
    stored_order = client.get(f"/api/vj-admin/pedidos/{order['id']}", headers=headers).json()

    assert confirmed.status_code == 400
    assert "estoque" in confirmed.json()["error"].lower()
    assert stock["produto"]["saldo_estoque"] == 1
    assert stock["movimentacoes"] == []
    assert stored_order["status"] == "rascunho"


def test_vj_admin_cancels_confirmed_order_and_returns_stock():
    headers = admin_headers()
    product = create_order_product(headers, "VJ-ORDER-CANCEL", estoque=5)
    order = create_order(headers, product, items=[{"produto_id": product["id"], "quantidade": 2}])
    client.post(f"/api/vj-admin/pedidos/{order['id']}/confirmar", headers=headers)

    canceled = client.post(f"/api/vj-admin/pedidos/{order['id']}/cancelar", headers=headers)
    stock = client.get(f"/api/vj-admin/produtos/{product['id']}/estoque", headers=headers).json()

    assert canceled.status_code == 200, canceled.text
    assert canceled.json()["status"] == "cancelado"
    assert stock["produto"]["saldo_estoque"] == 5
    assert [item["tipo"] for item in stock["movimentacoes"][:2]] == ["entrada", "saida"]


def test_vj_admin_order_calculates_total_profit_and_margin():
    headers = admin_headers()
    product = create_order_product(headers, "VJ-ORDER-CALC", estoque=5)

    order = create_order(
        headers,
        product,
        desconto_total=10,
        items=[{"produto_id": product["id"], "quantidade": 2}],
    )

    assert order["subtotal"] == 237.36
    assert order["desconto_total"] == 10.0
    assert order["taxa_pagamento"] == 0.0
    assert order["total"] == 227.36
    assert order["lucro_estimado"] == 108.68
    assert order["margem_estimada"] == 0.478
    assert order["items"][0]["preco_unitario"] == 118.68
    assert order["items"][0]["custo_unitario"] == 59.34
    assert order["items"][0]["lucro_unitario"] == 54.34

    with SessionLocal() as db:
        stored = db.get(Product, product["id"])
        assert stored.preco_pix == Decimal("118.68")


def test_vj_admin_blocks_editing_after_confirmation():
    headers = admin_headers()
    product = create_order_product(headers, "VJ-ORDER-EDIT-BLOCK", estoque=5)
    order = create_order(headers, product)
    client.post(f"/api/vj-admin/pedidos/{order['id']}/confirmar", headers=headers)

    edited = client.put(
        f"/api/vj-admin/pedidos/{order['id']}",
        headers=headers,
        json={
            "cliente_nome": "Cliente Editado",
            "forma_pagamento": "pix",
            "items": [{"produto_id": product["id"], "quantidade": 1}],
        },
    )

    assert edited.status_code == 400
    assert "editar" in edited.json()["error"].lower()


def test_vj_admin_canceled_order_cannot_be_canceled_again():
    headers = admin_headers()
    product = create_order_product(headers, "VJ-ORDER-CANCEL-TWICE", estoque=5)
    order = create_order(headers, product)
    first = client.post(f"/api/vj-admin/pedidos/{order['id']}/cancelar", headers=headers)
    second = client.post(f"/api/vj-admin/pedidos/{order['id']}/cancelar", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 400
    assert "novamente" in second.json()["error"].lower()


def test_vj_admin_confirmed_order_cannot_be_confirmed_again():
    headers = admin_headers()
    product = create_order_product(headers, "VJ-ORDER-CONFIRM-TWICE", estoque=5)
    order = create_order(headers, product)
    first = client.post(f"/api/vj-admin/pedidos/{order['id']}/confirmar", headers=headers)
    second = client.post(f"/api/vj-admin/pedidos/{order['id']}/confirmar", headers=headers)

    assert first.status_code == 200
    assert second.status_code == 400
    assert "novamente" in second.json()["error"].lower()


def test_vj_admin_lists_and_filters_simple_orders():
    headers = admin_headers()
    product = create_order_product(headers, "VJ-ORDER-LIST", estoque=5)
    included = create_order(headers, product, cliente_nome="Cliente Lista Especial")
    create_order(headers, product, cliente_nome="Cliente Fora")

    listed = client.get("/api/vj-admin/pedidos?search=lista", headers=headers)

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [included["id"]]


def decimal_money(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def test_vj_admin_order_with_multiple_items_distributes_discount_in_profit():
    headers = admin_headers()
    product_a = create_order_product(headers, "VJ-ORDER-MULTI-A", estoque=5, custo_peca=50)
    product_b = create_order_product(headers, "VJ-ORDER-MULTI-B", estoque=5, custo_peca=100)

    order = create_order(
        headers,
        product_a,
        desconto_total=45.60,
        items=[
            {"produto_id": product_a["id"], "quantidade": 2},
            {"produto_id": product_b["id"], "quantidade": 1},
        ],
    )

    subtotal = decimal_money(product_a["preco_pix"]) * 2 + decimal_money(product_b["preco_pix"])
    cost_total = decimal_money(product_a["custo_total"]) * 2 + decimal_money(product_b["custo_total"])
    total = subtotal - Decimal("45.60")
    expected_profit = total - cost_total
    summed_item_profit = sum(
        decimal_money(item["lucro_unitario"]) * item["quantidade"]
        for item in order["items"]
    )

    assert len(order["items"]) == 2
    assert decimal_money(order["subtotal"]) == subtotal
    assert decimal_money(order["total"]) == total
    assert decimal_money(order["lucro_estimado"]) == expected_profit
    assert abs(summed_item_profit - expected_profit) <= Decimal("0.02")
    assert order["items"][0]["lucro_unitario"] < product_a["preco_pix"] - product_a["custo_total"]
    assert order["items"][1]["lucro_unitario"] < product_b["preco_pix"] - product_b["custo_total"]


def test_vj_admin_order_blocks_inactive_product():
    headers = admin_headers()
    product = create_order_product(
        headers,
        "VJ-ORDER-INACTIVE-PRODUCT",
        estoque=5,
        status="inativo",
        publicado=False,
    )

    response = client.post(
        "/api/vj-admin/pedidos",
        headers=headers,
        json={
            "cliente_nome": "Cliente Inativo",
            "forma_pagamento": "pix",
            "items": [{"produto_id": product["id"], "quantidade": 1}],
        },
    )

    assert response.status_code == 400
    assert "inativo" in response.json()["error"].lower()


def test_confirmed_order_keeps_historical_price_and_cost_after_product_changes():
    headers = admin_headers()
    product = create_order_product(headers, "VJ-ORDER-HISTORICO", estoque=5, custo_peca=50)
    order = create_order(headers, product)
    confirmed = client.post(f"/api/vj-admin/pedidos/{order['id']}/confirmar", headers=headers).json()

    updated_product = client.put(
        f"/api/vj-admin/produtos/{product['id']}",
        headers=headers,
        json={"custo_peca": 100, "custo_embalagem": 20, "markup": 3},
    )
    fetched = client.get(f"/api/vj-admin/pedidos/{order['id']}", headers=headers).json()

    assert updated_product.status_code == 200
    assert updated_product.json()["preco_pix"] != confirmed["items"][0]["preco_unitario"]
    assert updated_product.json()["custo_total"] != confirmed["items"][0]["custo_unitario"]
    assert fetched["total"] == confirmed["total"]
    assert fetched["lucro_estimado"] == confirmed["lucro_estimado"]
    assert fetched["items"][0]["preco_unitario"] == confirmed["items"][0]["preco_unitario"]
    assert fetched["items"][0]["custo_unitario"] == confirmed["items"][0]["custo_unitario"]


def test_stale_double_confirmation_creates_only_one_stock_exit():
    headers = admin_headers()
    product = create_order_product(headers, "VJ-ORDER-STALE-CONFIRM", estoque=5)
    order = create_order(headers, product, items=[{"produto_id": product["id"], "quantidade": 2}])

    with SessionLocal() as stale_db:
        stale_order = stale_db.get(VJAdminOrder, order["id"])
        with SessionLocal() as fresh_db:
            fresh_order = fresh_db.get(VJAdminOrder, order["id"])
            confirm_vj_admin_order(fresh_db, fresh_order, actor_id=None)
            fresh_db.commit()
        try:
            confirm_vj_admin_order(stale_db, stale_order, actor_id=None)
            assert False, "segunda confirmacao deveria falhar"
        except ValueError as exc:
            stale_db.rollback()
            assert "novamente" in str(exc).lower()

    stock = client.get(f"/api/vj-admin/produtos/{product['id']}/estoque", headers=headers).json()
    exits = [item for item in stock["movimentacoes"] if item["tipo"] == "saida"]
    assert stock["produto"]["saldo_estoque"] == 3
    assert len(exits) == 1


def test_stale_double_cancel_returns_stock_only_once():
    headers = admin_headers()
    product = create_order_product(headers, "VJ-ORDER-STALE-CANCEL", estoque=5)
    order = create_order(headers, product, items=[{"produto_id": product["id"], "quantidade": 2}])
    client.post(f"/api/vj-admin/pedidos/{order['id']}/confirmar", headers=headers)

    with SessionLocal() as stale_db:
        stale_order = stale_db.get(VJAdminOrder, order["id"])
        with SessionLocal() as fresh_db:
            fresh_order = fresh_db.get(VJAdminOrder, order["id"])
            cancel_vj_admin_order(fresh_db, fresh_order, actor_id=None)
            fresh_db.commit()
        try:
            cancel_vj_admin_order(stale_db, stale_order, actor_id=None)
            assert False, "segundo cancelamento deveria falhar"
        except ValueError as exc:
            stale_db.rollback()
            assert "novamente" in str(exc).lower()

    stock = client.get(f"/api/vj-admin/produtos/{product['id']}/estoque", headers=headers).json()
    entries = [item for item in stock["movimentacoes"] if item["tipo"] == "entrada"]
    assert stock["produto"]["saldo_estoque"] == 5
    assert len(entries) == 1


