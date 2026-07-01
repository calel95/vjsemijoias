from datetime import UTC, datetime

from tests.helpers import admin_headers, client, order_payload
from tests.test_vj_admin_finance import (
    confirm_order,
    create_expense,
    create_finance_customer,
    create_finance_order,
    create_finance_product,
    set_order_date,
)


def audit_logs(headers, **filters):
    response = client.get("/api/vj-admin/auditoria", headers=headers, params=filters)
    assert response.status_code == 200, response.text
    return response.json()


def assert_audit_log(headers, *, action, resource, resource_id):
    logs = audit_logs(headers, action=action, recurso=resource)
    matches = [log for log in logs if log["resource_id"] == str(resource_id)]
    assert matches, logs[:5]
    assert matches[0]["admin_user_id"] is not None
    assert matches[0]["admin_email"] == "admin@vjsemijoias.com"
    assert matches[0]["ip_address"]
    assert matches[0]["user_agent"] is not None
    return matches[0]


def test_vj_admin_audit_logs_confirm_order():
    headers = admin_headers()
    product = create_finance_product(headers, "VJ-AUD-CONFIRM")
    order = create_finance_order(headers, product)

    confirmed = confirm_order(headers, order)

    log = assert_audit_log(headers, action="pedido_confirmado", resource="pedido", resource_id=confirmed["id"])
    assert log["metadata"]["status"] == "confirmado"
    assert log["metadata"]["itens"] == 1


def test_vj_admin_audit_logs_cancel_order():
    headers = admin_headers()
    product = create_finance_product(headers, "VJ-AUD-CANCEL")
    order = create_finance_order(headers, product)

    canceled = client.post(f"/api/vj-admin/pedidos/{order['id']}/cancelar", headers=headers)

    assert canceled.status_code == 200, canceled.text
    log = assert_audit_log(headers, action="pedido_cancelado", resource="pedido", resource_id=order["id"])
    assert log["metadata"]["status"] == "cancelado"


def test_vj_admin_audit_logs_stock_movement():
    headers = admin_headers()
    product = create_finance_product(headers, "VJ-AUD-STOCK", estoque=4)

    moved = client.post(
        f"/api/vj-admin/produtos/{product['id']}/estoque/movimentar",
        headers=headers,
        json={"tipo": "entrada", "quantidade": 2, "motivo": "Auditoria estoque"},
    )

    assert moved.status_code == 201, moved.text
    movement_id = moved.json()["movimentacao"]["id"]
    log = assert_audit_log(headers, action="estoque_movimentado", resource="estoque", resource_id=movement_id)
    assert log["metadata"]["produto_id"] == product["id"]
    assert log["metadata"]["tipo"] == "entrada"
    assert log["metadata"]["quantidade"] == 2


def test_vj_admin_audit_logs_deactivate_customer():
    headers = admin_headers()
    customer = create_finance_customer(headers, "Cliente Auditoria Inativar")

    inactive = client.post(f"/api/vj-admin/clientes/{customer['id']}/inativar", headers=headers)

    assert inactive.status_code == 200, inactive.text
    log = assert_audit_log(headers, action="cliente_inativado", resource="cliente", resource_id=customer["id"])
    assert log["metadata"]["status"] == "inativo"


def test_vj_admin_audit_list_filters_by_action_resource_and_date():
    headers = admin_headers()
    product = create_finance_product(headers, "VJ-AUD-FILTER")
    today = datetime.now(UTC).date().isoformat()

    published = client.post(f"/api/vj-admin/produtos/{product['id']}/publicar", headers=headers)

    assert published.status_code == 200, published.text
    logs = audit_logs(
        headers,
        action="produto_publicado",
        recurso="produto",
        data_inicio=today,
        data_fim=today,
    )

    assert any(log["resource_id"] == str(product["id"]) for log in logs)
    assert all(log["action"] == "produto_publicado" for log in logs)
    assert all(log["resource"] == "produto" for log in logs)


def test_vj_admin_exports_customers_csv():
    headers = admin_headers()
    included = create_finance_customer(headers, "Cliente CSV Auditoria")
    create_finance_customer(headers, "Cliente CSV Fora")

    response = client.get("/api/vj-admin/clientes/export.csv?search=Cliente%20CSV%20Auditoria", headers=headers)
    content = response.content.decode("utf-8-sig")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "id,nome,whatsapp,email" in content
    assert included["nome"] in content
    assert "Cliente CSV Fora" not in content


def test_vj_admin_exports_orders_csv():
    headers = admin_headers()
    product = create_finance_product(headers, "VJ-ORDER-CSV")
    order = create_finance_order(headers, product, cliente_nome="Cliente Pedido CSV")

    response = client.get("/api/vj-admin/pedidos/export.csv?search=Cliente%20Pedido%20CSV", headers=headers)
    content = response.content.decode("utf-8-sig")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "id,status,customer_id,cliente_nome" in content
    assert str(order["id"]) in content
    assert "Cliente Pedido CSV" in content


def test_vj_admin_exports_expenses_csv():
    headers = admin_headers()
    expense = create_expense(headers, descricao="Despesa CSV Auditoria", categoria="Auditoria", data="2026-04-01")

    response = client.get(
        "/api/vj-admin/financeiro/despesas/export.csv?categoria=auditoria&data_inicio=2026-04-01&data_fim=2026-04-01",
        headers=headers,
    )
    content = response.content.decode("utf-8-sig")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "id,descricao,categoria,valor" in content
    assert expense["descricao"] in content


def test_vj_admin_exports_finance_summary_csv():
    headers = admin_headers()
    day = "2026-04-02"
    product = create_finance_product(headers, "VJ-SUMMARY-CSV")
    order = set_order_date(confirm_order(headers, create_finance_order(headers, product)), day)
    create_expense(headers, descricao="Despesa resumo CSV", valor=9, data=day)

    response = client.get(
        f"/api/vj-admin/financeiro/resumo/export.csv?data_inicio={day}&data_fim={day}",
        headers=headers,
    )
    content = response.content.decode("utf-8-sig")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "secao,chave,valor,quantidade,extra" in content
    assert "faturamento_bruto" in content
    assert str(order["subtotal"]) in content


def test_public_checkout_is_not_affected_by_vj_admin_audit():
    response = client.post("/api/orders", json=order_payload())

    assert response.status_code == 201, response.text
    assert response.json()["customer_name"] == "Cliente Teste"