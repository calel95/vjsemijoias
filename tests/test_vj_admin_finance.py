from datetime import UTC, datetime
from decimal import Decimal

from backend.database import SessionLocal
from backend.models import VJAdminOrder
from tests.helpers import admin_headers, client, order_payload


def create_finance_product(headers, code, **overrides):
    payload = {
        "codigo": code,
        "nome": f"Produto Financeiro {code}",
        "categoria": "aneis",
        "descricao": "Produto para testes financeiros.",
        "custo_peca": 50,
        "estoque": 10,
        "status": "publicado",
        "publicado": True,
    }
    payload.update(overrides)
    response = client.post("/api/vj-admin/produtos", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def create_finance_customer(headers, nome="Cliente Financeiro"):
    response = client.post(
        "/api/vj-admin/clientes",
        headers=headers,
        json={
            "nome": nome,
            "whatsapp": "11999999999",
            "email": f"{nome.lower().replace(' ', '-')}@example.com",
            "origem": "Instagram",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_finance_order(headers, product, **overrides):
    payload = {
        "cliente_nome": "Cliente Financeiro Avulso",
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


def confirm_order(headers, order):
    response = client.post(f"/api/vj-admin/pedidos/{order['id']}/confirmar", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def set_order_date(order, value):
    timestamp = datetime.fromisoformat(f"{value}T12:00:00+00:00").astimezone(UTC)
    with SessionLocal() as db:
        model = db.get(VJAdminOrder, order["id"])
        assert model is not None
        model.created_at = timestamp
        model.updated_at = timestamp
        db.commit()
    order["created_at"] = timestamp.isoformat()
    order["updated_at"] = timestamp.isoformat()
    return order


def finance_summary(headers, value):
    response = client.get(
        f"/api/vj-admin/financeiro/resumo?data_inicio={value}&data_fim={value}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def create_expense(headers, **overrides):
    payload = {
        "descricao": "Embalagens extras",
        "categoria": "Operacional",
        "valor": 25,
        "data": "2026-06-15",
        "observacoes": "Compra manual",
    }
    payload.update(overrides)
    response = client.post("/api/vj-admin/financeiro/despesas", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_vj_admin_finance_creates_expense():
    headers = admin_headers()

    expense = create_expense(headers, descricao="Taxa marketplace", valor="42.50")

    assert expense["descricao"] == "Taxa marketplace"
    assert expense["categoria"] == "Operacional"
    assert expense["valor"] == 42.5
    assert expense["data"] == "2026-06-15"
    assert expense["status"] == "ativo"


def test_vj_admin_finance_edits_expense():
    headers = admin_headers()
    expense = create_expense(headers, descricao="Despesa editar")

    edited = client.put(
        f"/api/vj-admin/financeiro/despesas/{expense['id']}",
        headers=headers,
        json={"descricao": "Despesa editada", "categoria": "Marketing", "valor": 33.75},
    )

    assert edited.status_code == 200, edited.text
    data = edited.json()
    assert data["descricao"] == "Despesa editada"
    assert data["categoria"] == "Marketing"
    assert data["valor"] == 33.75


def test_vj_admin_finance_cancels_expense():
    headers = admin_headers()
    expense = create_expense(headers, descricao="Despesa cancelar")

    canceled = client.post(f"/api/vj-admin/financeiro/despesas/{expense['id']}/cancelar", headers=headers)
    listed = client.get("/api/vj-admin/financeiro/despesas?status=cancelado", headers=headers)

    assert canceled.status_code == 200, canceled.text
    assert canceled.json()["status"] == "cancelado"
    assert any(item["id"] == expense["id"] for item in listed.json())


def test_vj_admin_finance_lists_expenses_with_filters():
    headers = admin_headers()
    day = "2026-01-04"
    included = create_expense(headers, descricao="Anuncio filtrado", categoria="Marketing", valor=44, data=day)
    create_expense(headers, descricao="Categoria fora", categoria="Operacional", valor=30, data=day)
    create_expense(headers, descricao="Data fora", categoria="Marketing", valor=30, data="2026-01-03")
    canceled = create_expense(headers, descricao="Cancelada fora", categoria="Marketing", valor=30, data=day)
    client.post(f"/api/vj-admin/financeiro/despesas/{canceled['id']}/cancelar", headers=headers)

    response = client.get(
        f"/api/vj-admin/financeiro/despesas?data_inicio={day}&data_fim={day}&status=ativo&categoria=marketing",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    assert [item["id"] for item in response.json()] == [included["id"]]


def test_vj_admin_finance_rejects_invalid_filters():
    headers = admin_headers()

    invalid_status = client.get("/api/vj-admin/financeiro/despesas?status=invalido", headers=headers)
    invalid_period = client.get(
        "/api/vj-admin/financeiro/resumo?data_inicio=2026-02-01&data_fim=2026-01-01",
        headers=headers,
    )

    assert invalid_status.status_code == 400
    assert invalid_period.status_code == 400

def test_vj_admin_finance_summary_ignores_canceled_expenses():
    headers = admin_headers()
    day = "2026-01-05"
    create_expense(headers, descricao="Despesa ativa", valor=20, data=day)
    canceled = create_expense(headers, descricao="Despesa cancelada", valor=999, data=day)
    client.post(f"/api/vj-admin/financeiro/despesas/{canceled['id']}/cancelar", headers=headers)

    summary = finance_summary(headers, day)

    assert summary["despesas"] == 20.0


def test_vj_admin_finance_summary_considers_only_confirmed_orders():
    headers = admin_headers()
    day = "2026-01-06"
    product = create_finance_product(headers, "VJ-FIN-STATUS")
    confirmed = set_order_date(confirm_order(headers, create_finance_order(headers, product)), day)
    draft = set_order_date(create_finance_order(headers, product), day)
    canceled = set_order_date(create_finance_order(headers, product), day)
    client.post(f"/api/vj-admin/pedidos/{canceled['id']}/cancelar", headers=headers)

    summary = finance_summary(headers, day)

    assert summary["quantidade_pedidos_confirmados"] == 1
    assert summary["faturamento_bruto"] == confirmed["subtotal"]
    assert draft["status"] == "rascunho"


def test_vj_admin_finance_summary_calculates_core_values():
    headers = admin_headers()
    day = "2026-01-07"
    product = create_finance_product(headers, "VJ-FIN-CALC", custo_peca=50)
    order = set_order_date(
        confirm_order(
            headers,
            create_finance_order(
                headers,
                product,
                desconto_total=10,
                items=[{"produto_id": product["id"], "quantidade": 2}],
            ),
        ),
        day,
    )
    create_expense(headers, descricao="Despesa calculo", valor=30, data=day)

    summary = finance_summary(headers, day)

    expected_cost = float((Decimal(str(order["items"][0]["custo_unitario"])) * Decimal("2")).quantize(Decimal("0.01")))
    assert summary["faturamento_bruto"] == order["subtotal"]
    assert summary["total_descontos"] == 10.0
    assert summary["taxas_pagamento"] == order["taxa_pagamento"]
    assert summary["custo_produtos_vendidos"] == expected_cost
    assert summary["lucro_bruto"] == order["lucro_estimado"]
    assert summary["despesas"] == 30.0
    assert summary["lucro_liquido_estimado"] == round(order["lucro_estimado"] - 30.0, 2)
    assert summary["ticket_medio"] == order["total"]


def test_vj_admin_finance_product_ranking():
    headers = admin_headers()
    day = "2026-01-08"
    product_a = create_finance_product(headers, "VJ-FIN-RANK-A")
    product_b = create_finance_product(headers, "VJ-FIN-RANK-B")
    set_order_date(confirm_order(headers, create_finance_order(headers, product_a, items=[{"produto_id": product_a["id"], "quantidade": 3}])), day)
    set_order_date(confirm_order(headers, create_finance_order(headers, product_b, items=[{"produto_id": product_b["id"], "quantidade": 1}])), day)

    ranking = finance_summary(headers, day)["ranking_produtos"]

    assert ranking[0]["produto_id"] == product_a["id"]
    assert ranking[0]["quantidade"] == 3
    assert ranking[1]["produto_id"] == product_b["id"]


def test_vj_admin_finance_customer_ranking():
    headers = admin_headers()
    day = "2026-01-09"
    product = create_finance_product(headers, "VJ-FIN-CUSTOMER-RANK")
    customer_a = create_finance_customer(headers, "Cliente Ranking A")
    customer_b = create_finance_customer(headers, "Cliente Ranking B")
    set_order_date(confirm_order(headers, create_finance_order(headers, product, customer_id=customer_a["id"], items=[{"produto_id": product["id"], "quantidade": 2}])), day)
    set_order_date(confirm_order(headers, create_finance_order(headers, product, customer_id=customer_b["id"], items=[{"produto_id": product["id"], "quantidade": 1}])), day)

    ranking = finance_summary(headers, day)["ranking_clientes"]

    assert ranking[0]["customer_id"] == customer_a["id"]
    assert ranking[0]["quantidade_pedidos"] == 1
    assert ranking[1]["customer_id"] == customer_b["id"]


def test_vj_admin_finance_filters_by_period():
    headers = admin_headers()
    day = "2026-01-10"
    product = create_finance_product(headers, "VJ-FIN-PERIOD")
    confirmed = set_order_date(confirm_order(headers, create_finance_order(headers, product)), day)
    create_expense(headers, descricao="Despesa periodo", valor=12, data=day)

    included = finance_summary(headers, day)
    excluded = client.get(
        "/api/vj-admin/financeiro/resumo?data_inicio=1999-01-01&data_fim=1999-01-31",
        headers=headers,
    ).json()

    assert included["quantidade_pedidos_confirmados"] == 1
    assert included["faturamento_bruto"] == confirmed["subtotal"]
    assert included["despesas"] == 12.0
    assert excluded["quantidade_pedidos_confirmados"] == 0
    assert excluded["despesas"] == 0.0


def test_vj_admin_finance_payment_summary():
    headers = admin_headers()
    day = "2026-01-11"
    product = create_finance_product(headers, "VJ-FIN-PAYMENT")
    set_order_date(confirm_order(headers, create_finance_order(headers, product, forma_pagamento="pix")), day)
    set_order_date(confirm_order(headers, create_finance_order(headers, product, forma_pagamento="credito", parcelas=2)), day)

    payments = finance_summary(headers, day)["resumo_pagamentos"]
    methods = {item["forma_pagamento"]: item for item in payments}

    assert methods["pix"]["quantidade_pedidos"] == 1
    assert methods["credito"]["quantidade_pedidos"] == 1
    assert methods["credito"]["taxas"] > 0


def test_public_checkout_is_not_affected_by_vj_admin_finance():
    response = client.post("/api/orders", json=order_payload())

    assert response.status_code == 201, response.text
    assert response.json()["customer_name"] == "Cliente Teste"
