import os
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ADMIN_PASSWORD"] = "test-admin-password"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-with-at-least-32-bytes"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["INFINITEPAY_HANDLE"] = "vjsemijoias"
os.environ["PUBLIC_BASE_URL"] = "https://vj.example.com"
os.environ["SHIPPING_MODE"] = "free"
os.environ["COUPONS_ENABLED"] = "true"
os.environ["COUPON_CODE"] = "VJ10"
os.environ["COUPON_DISCOUNT_PERCENT"] = "10"
os.environ["COUPON_USAGE_LIMIT"] = "100"
os.environ["CSRF_COOKIE_SECURE"] = "false"

from fastapi.testclient import TestClient

from backend.database import Base, engine
import backend.models  # noqa: F401

Base.metadata.create_all(engine)

from backend.app import ADMIN_LOGIN_ATTEMPTS, app
from backend.config import settings


client = TestClient(app)


class FakeResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.text = ""

    def json(self):
        return self.data


def assert_status(response, expected, label):
    if response.status_code != expected:
        raise AssertionError(
            f"{label}: esperado HTTP {expected}, veio {response.status_code}: "
            f"{response.text[:500]}"
        )
    return response


def assert_true(condition, label):
    if not condition:
        raise AssertionError(label)


def log_step(message):
    print(f"[OK] {message}")


def csrf_headers():
    token = client.cookies.get(settings.csrf_cookie_name)
    return {settings.csrf_header_name: token} if token else {}


@contextmanager
def fake_infinitepay():
    def fake_request(self, method, url, **kwargs):
        assert_true(self.trust_env is False, "InfinitePay deve ignorar proxy local")
        if url.endswith("/links"):
            payload = kwargs["json"]
            assert_true(payload["handle"] == "vjsemijoias", "handle InfinitePay incorreto")
            assert_true(
                payload["redirect_url"] == "https://vj.example.com/checkout",
                "redirect_url do checkout incorreto",
            )
            assert_true(
                payload["webhook_url"]
                == "https://vj.example.com/api/payments/webhook/infinitepay",
                "webhook_url do checkout incorreto",
            )
            return FakeResponse({"url": "https://checkout.infinitepay.com.br/e2e"})
        if url.endswith("/payment_check"):
            payload = kwargs["json"]
            assert_true(payload["handle"] == "vjsemijoias", "handle do payment_check incorreto")
            return FakeResponse(
                {
                    "success": True,
                    "paid": True,
                    "amount": 13491,
                    "paid_amount": 13491,
                    "installments": 1,
                    "capture_method": "pix",
                }
            )
        return FakeResponse({"message": "rota fake nao esperada"}, status_code=404)

    with patch("backend.infinitepay_client.requests.Session.request", fake_request):
        yield


def run():
    ADMIN_LOGIN_ATTEMPTS.clear()

    assert_status(client.get("/api/health"), 200, "health")
    for path in ["/", "/catalogo", "/produto", "/carrinho", "/checkout", "/admin"]:
        response = assert_status(client.get(path), 200, f"pagina {path}")
        assert_true("<!DOCTYPE html>" in response.text, f"{path} deve retornar HTML")
    log_step("paginas publicas e health respondem")

    products_response = assert_status(client.get("/api/products"), 200, "catalogo publico")
    products = products_response.json()
    assert_true(len(products) >= 10, "catalogo publico deve ter produtos seed")
    product_id = products[0]["id"]
    assert_status(client.get(f"/api/products/{product_id}"), 200, "detalhe de produto")
    log_step(f"catalogo publico carregou {len(products)} produtos")

    store_config = assert_status(client.get("/api/store/config"), 200, "config da loja").json()
    assert_true(store_config["shipping"]["mode"] == "free", "frete deveria estar gratis no e2e")
    shipping = assert_status(
        client.post("/api/shipping/calculate", json={"total": 149.9, "zip_code": "01001000"}),
        200,
        "calculo de frete",
    ).json()
    assert_true(shipping["shipping"] == 0, "frete e2e deveria ser zero")
    log_step("configuracao de loja, frete e cupom respondem")

    assert_status(client.post("/api/products", json={}), 401, "admin sem token")
    user = assert_status(
        client.post(
            "/api/auth/register",
            json={
                "name": "Cliente E2E",
                "email": "cliente-e2e@example.com",
                "password": "senha123",
            },
        ),
        201,
        "cadastro usuario comum",
    ).json()
    assert_status(
        client.get(
            "/api/admin/products",
            headers={"Authorization": f"Bearer {user['token']}"},
        ),
        403,
        "token comum em rota admin",
    )
    admin_login = assert_status(
        client.post("/api/auth/admin/login", json={"password": "test-admin-password"}),
        200,
        "login admin",
    ).json()
    admin_token = admin_login["token"]
    assert_true(admin_login["token_type"] == "admin", "login admin deve emitir token admin")
    log_step("autenticacao admin e bloqueio de token comum validados")

    headers = {"Authorization": f"Bearer {admin_token}"}
    created = assert_status(
        client.post(
            "/api/products",
            headers=headers,
            json={
                "name": "Produto E2E",
                "category": "colares",
                "categoryName": "Colares",
                "price": 88.9,
                "description": "Produto criado pelo smoke test.",
                "features": ["Banho de ouro 18k"],
                "stock_status": "available",
            },
        ),
        201,
        "criar produto admin",
    ).json()
    updated = assert_status(
        client.put(
            f"/api/products/{created['id']}",
            headers=headers,
            json={**created, "price": 99.9, "is_active": False},
        ),
        200,
        "editar produto admin",
    ).json()
    assert_true(updated["price"] == 99.9, "edicao de produto nao persistiu preco")
    assert_status(client.get(f"/api/products/{created['id']}"), 404, "produto inativo publico")
    assert_status(
        client.delete(f"/api/products/{created['id']}", headers=headers),
        200,
        "excluir produto admin",
    )
    log_step("CRUD principal de produtos pelo admin validado")

    order_payload = {
        "customer_name": "Cliente Checkout",
        "customer_email": "checkout-e2e@example.com",
        "customer_cpf": "12345678909",
        "customer_phone": "51982110842",
        "address_zip": "01001000",
        "address_street": "Rua Teste",
        "address_number": "123",
        "address_neighborhood": "Centro",
        "address_city": "Sao Paulo",
        "address_state": "SP",
        "items": [{"id": product_id, "quantity": 1}],
        "coupon": "VJ10",
    }
    with fake_infinitepay():
        checkout = assert_status(
            client.post(
                "/api/payments/infinitepay/checkout",
                headers=csrf_headers(),
                json=order_payload,
            ),
            201,
            "checkout InfinitePay",
        ).json()
        assert_true(
            checkout["checkout_url"] == "https://checkout.infinitepay.com.br/e2e",
            "checkout_url inesperada",
        )
        status = assert_status(
            client.get(
                f"/api/payments/{checkout['order']['id']}/status"
                f"?token={checkout['payment']['checkout_token']}"
            ),
            200,
            "status pagamento pendente",
        ).json()
        assert_true(status["status"] == "pending", "pagamento deveria iniciar pendente")
        assert_true(
            checkout["order"]["status"] == "payment_pending",
            "pedido deveria aguardar pagamento apos checkout",
        )
        confirmed = assert_status(
            client.post(
                "/api/payments/infinitepay/confirm",
                headers=csrf_headers(),
                json={
                    "order_nsu": checkout["order"]["id"],
                    "transaction_nsu": "transaction-e2e",
                    "slug": "invoice-e2e",
                },
            ),
            200,
            "confirmacao pagamento",
        ).json()
        assert_true(confirmed["payment"]["status"] == "paid", "pagamento deveria confirmar")
        assert_true(confirmed["order"]["status"] == "paid", "pedido deveria ficar pago")
    log_step("checkout, status e confirmacao InfinitePay simulada validados")

    stats = assert_status(client.get("/api/admin/stats", headers=headers), 200, "stats admin").json()
    orders = assert_status(client.get("/api/orders", headers=headers), 200, "pedidos admin").json()
    assert_true(stats["total_products"] >= 10, "stats admin sem produtos")
    assert_true(any(order["id"] == confirmed["order"]["id"] for order in orders), "pedido nao aparece no admin")
    log_step("dashboard admin e listagem de pedidos validados")

    print("\nSmoke E2E concluido com sucesso.")


if __name__ == "__main__":
    run()
