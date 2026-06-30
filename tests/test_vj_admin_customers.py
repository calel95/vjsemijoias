from tests.helpers import admin_headers, client, order_payload


def create_customer(headers, **overrides):
    payload = {
        "nome": "Cliente CRM",
        "whatsapp": "+55 (11) 99999-9999",
        "email": "CLIENTE.CRM@EXAMPLE.COM",
        "cpf": "123.456.789-09",
        "instagram": "@clientecrm",
        "cidade": "Sao Paulo",
        "estado": "sp",
        "data_nascimento": "1990-05-20",
        "observacoes": "Cliente prefere pix.",
        "origem": "Instagram",
    }
    payload.update(overrides)
    response = client.post("/api/vj-admin/clientes", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_customer_product(headers, code, **overrides):
    payload = {
        "codigo": code,
        "nome": f"Produto Cliente {code}",
        "categoria": "colares",
        "descricao": "Produto para testes de cliente.",
        "custo_peca": 50,
        "estoque": 8,
        "status": "publicado",
        "publicado": True,
    }
    payload.update(overrides)
    response = client.post("/api/vj-admin/produtos", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_customer_order(headers, product, **overrides):
    payload = {
        "cliente_nome": "Cliente Avulso",
        "cliente_whatsapp": "11988887777",
        "forma_pagamento": "pix",
        "parcelas": 1,
        "desconto_total": 0,
        "items": [{"produto_id": product["id"], "quantidade": 1}],
    }
    payload.update(overrides)
    response = client.post("/api/vj-admin/pedidos", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_vj_admin_creates_customer_with_normalized_contact_fields():
    headers = admin_headers()

    customer = create_customer(headers, nome="Cliente Normalizacao")

    assert customer["nome"] == "Cliente Normalizacao"
    assert customer["whatsapp"] == "11999999999"
    assert customer["email"] == "cliente.crm@example.com"
    assert customer["cpf"] == "12345678909"
    assert customer["instagram"] == "clientecrm"
    assert customer["estado"] == "SP"
    assert customer["status"] == "ativo"


def test_vj_admin_edits_customer():
    headers = admin_headers()
    customer = create_customer(headers, nome="Cliente Edicao")

    edited = client.put(
        f"/api/vj-admin/clientes/{customer['id']}",
        headers=headers,
        json={"nome": "Cliente Editada", "email": "EDITADA@EXAMPLE.COM", "cidade": "Campinas"},
    )

    assert edited.status_code == 200, edited.text
    data = edited.json()
    assert data["nome"] == "Cliente Editada"
    assert data["email"] == "editada@example.com"
    assert data["cidade"] == "Campinas"


def test_vj_admin_lists_customers_with_search_and_filters():
    headers = admin_headers()
    included = create_customer(
        headers,
        nome="Cliente Busca Especial",
        email="busca-especial@example.com",
        instagram="@buscaespecial",
        cidade="Curitiba",
        origem="Feira",
    )
    create_customer(headers, nome="Cliente Fora Busca", cidade="Recife", origem="Instagram")

    listed = client.get(
        "/api/vj-admin/clientes?search=especial&status=ativo&cidade=curitiba&origem=feira",
        headers=headers,
    )

    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()] == [included["id"]]


def test_vj_admin_inactivates_customer_without_deleting():
    headers = admin_headers()
    customer = create_customer(headers, nome="Cliente Inativar")

    inactivated = client.post(f"/api/vj-admin/clientes/{customer['id']}/inativar", headers=headers)
    fetched = client.get(f"/api/vj-admin/clientes/{customer['id']}", headers=headers)

    assert inactivated.status_code == 200, inactivated.text
    assert inactivated.json()["status"] == "inativo"
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "inativo"


def test_vj_admin_blocks_inactive_customer_in_new_order():
    headers = admin_headers()
    customer = create_customer(headers, nome="Cliente Bloqueado")
    client.post(f"/api/vj-admin/clientes/{customer['id']}/inativar", headers=headers)
    product = create_customer_product(headers, "VJ-CUSTOMER-INACTIVE")

    response = client.post(
        "/api/vj-admin/pedidos",
        headers=headers,
        json={
            "customer_id": customer["id"],
            "forma_pagamento": "pix",
            "items": [{"produto_id": product["id"], "quantidade": 1}],
        },
    )

    assert response.status_code == 400
    assert "inativo" in response.json()["error"].lower()


def test_vj_admin_creates_order_linked_to_customer():
    headers = admin_headers()
    customer = create_customer(headers, nome="Cliente Pedido Vinculado", whatsapp="(11) 98888-7777")
    product = create_customer_product(headers, "VJ-CUSTOMER-LINK")

    order = create_customer_order(headers, product, customer_id=customer["id"], cliente_nome="Ignorar")

    assert order["customer_id"] == customer["id"]
    assert order["cliente_nome"] == "Cliente Pedido Vinculado"
    assert order["cliente_whatsapp"] == "11988887777"
    assert order["customer"]["id"] == customer["id"]


def test_vj_admin_lists_customer_orders_and_metrics():
    headers = admin_headers()
    customer = create_customer(headers, nome="Cliente Metricas")
    product = create_customer_product(headers, "VJ-CUSTOMER-METRICS")
    confirmed = create_customer_order(headers, product, customer_id=customer["id"])
    draft = create_customer_order(headers, product, customer_id=customer["id"])
    client.post(f"/api/vj-admin/pedidos/{confirmed['id']}/confirmar", headers=headers)

    response = client.get(f"/api/vj-admin/clientes/{customer['id']}/pedidos", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()
    assert [order["id"] for order in data["pedidos"]] == [draft["id"], confirmed["id"]]
    assert data["metricas"]["quantidade_pedidos"] == 1
    assert data["metricas"]["total_gasto"] == confirmed["total"]
    assert data["metricas"]["ticket_medio"] == confirmed["total"]
    assert data["metricas"]["ultima_compra"]


def test_public_checkout_is_not_affected_by_vj_admin_customers():
    response = client.post("/api/orders", json=order_payload())

    assert response.status_code == 201, response.text
    assert response.json()["customer_name"] == "Cliente Teste"