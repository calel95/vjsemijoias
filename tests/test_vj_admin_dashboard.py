from tests.helpers import admin_headers, client
from tests.test_vj_admin_finance import (
    confirm_order,
    create_expense,
    create_finance_customer,
    create_finance_order,
    create_finance_product,
    set_order_date,
)


def dashboard(headers, day):
    response = client.get(
        f"/api/vj-admin/dashboard?periodo=personalizado&data_inicio={day}&data_fim={day}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_vj_admin_dashboard_endpoint():
    headers = admin_headers()

    response = client.get("/api/vj-admin/dashboard", headers=headers)

    assert response.status_code == 200, response.text
    data = response.json()
    for key in [
        "faturamento_mes",
        "lucro_liquido_estimado_mes",
        "pedidos_confirmados_mes",
        "ticket_medio_mes",
        "clientes_ativos",
        "produtos_ativos_publicados",
        "produtos_estoque_baixo",
        "produtos_sem_estoque",
        "top_produtos",
        "top_clientes",
        "resumo_pagamentos",
        "despesas_mes",
        "margem_liquida_estimada",
    ]:
        assert key in data


def test_vj_admin_dashboard_filters_by_period():
    headers = admin_headers()
    included_day = "2026-03-01"
    excluded_day = "2026-03-02"
    product = create_finance_product(headers, "VJ-DASH-PERIOD")
    included = set_order_date(confirm_order(headers, create_finance_order(headers, product)), included_day)
    set_order_date(confirm_order(headers, create_finance_order(headers, product)), excluded_day)
    create_expense(headers, descricao="Despesa dashboard periodo", valor=15, data=included_day)

    data = dashboard(headers, included_day)

    assert data["data_inicio"] == included_day
    assert data["data_fim"] == included_day
    assert data["pedidos_confirmados_mes"] == 1
    assert data["faturamento_mes"] == included["subtotal"]
    assert data["despesas_mes"] == 15.0


def test_vj_admin_dashboard_ignores_canceled_and_draft_orders():
    headers = admin_headers()
    day = "2026-03-03"
    product = create_finance_product(headers, "VJ-DASH-STATUS")
    confirmed = set_order_date(confirm_order(headers, create_finance_order(headers, product)), day)
    set_order_date(create_finance_order(headers, product), day)
    canceled = set_order_date(create_finance_order(headers, product), day)
    client.post(f"/api/vj-admin/pedidos/{canceled['id']}/cancelar", headers=headers)

    data = dashboard(headers, day)

    assert data["pedidos_confirmados_mes"] == 1
    assert data["faturamento_mes"] == confirmed["subtotal"]


def test_vj_admin_dashboard_counts_low_and_out_of_stock_products():
    headers = admin_headers()
    day = "2026-03-04"
    before = dashboard(headers, day)

    create_finance_product(headers, "VJ-DASH-LOW", estoque=1)
    create_finance_product(headers, "VJ-DASH-OUT", estoque=0)

    after = dashboard(headers, day)

    assert after["produtos_estoque_baixo"] >= before["produtos_estoque_baixo"] + 1
    assert after["produtos_sem_estoque"] >= before["produtos_sem_estoque"] + 1
    assert after["produtos_ativos_publicados"] >= before["produtos_ativos_publicados"] + 2


def test_vj_admin_dashboard_top_products_clients_and_payments():
    headers = admin_headers()
    day = "2026-03-05"
    low_product = create_finance_product(headers, "VJ-DASH-RANK-LOW", custo_peca=10)
    high_product = create_finance_product(headers, "VJ-DASH-RANK-HIGH", custo_peca=200)
    customer_low = create_finance_customer(headers, "Cliente Dashboard Baixo")
    customer_high = create_finance_customer(headers, "Cliente Dashboard Alto")

    set_order_date(
        confirm_order(
            headers,
            create_finance_order(
                headers,
                low_product,
                customer_id=customer_low["id"],
                forma_pagamento="pix",
                items=[{"produto_id": low_product["id"], "quantidade": 2}],
            ),
        ),
        day,
    )
    set_order_date(
        confirm_order(
            headers,
            create_finance_order(
                headers,
                high_product,
                customer_id=customer_high["id"],
                forma_pagamento="credito",
                parcelas=2,
                items=[{"produto_id": high_product["id"], "quantidade": 1}],
            ),
        ),
        day,
    )

    data = dashboard(headers, day)
    products = data["top_produtos"]
    clients = data["top_clientes"]
    payments = {item["forma_pagamento"]: item for item in data["resumo_pagamentos"]}

    assert products[0]["produto_id"] == high_product["id"]
    assert products[0]["faturamento"] > products[1]["faturamento"]
    assert clients[0]["customer_id"] == customer_high["id"]
    assert payments["pix"]["quantidade_pedidos"] == 1
    assert payments["credito"]["quantidade_pedidos"] == 1
    assert payments["credito"]["taxas"] > 0


def test_vj_admin_dashboard_rejects_invalid_period():
    headers = admin_headers()

    response = client.get("/api/vj-admin/dashboard?periodo=invalido", headers=headers)

    assert response.status_code == 400