from fastapi.testclient import TestClient

from backend.app import app
from backend.database import SessionLocal
from backend.import_products import DEFAULT_SOURCE
from backend.models import StoreSetting
from backend.services.startup import sync_default_coupon

import json


ADMIN_EMAIL = "admin@vjsemijoias.com"
TINY_GIF_DATA_URL = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
TINY_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff,"
    b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x01L\x00;"
)


class FakeResponse:
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.text = ""

    def json(self):
        return self.data


client = TestClient(app)


def admin_login(
    email=ADMIN_EMAIL,
    password="test-admin-password",
    *,
    persist_cookie=False,
    api_client=client,
):
    response = api_client.post(
        "/api/auth/admin/login",
        json={"email": email, "password": password},
    )
    if not persist_cookie:
        api_client.cookies.clear()
    return response


def admin_headers():
    login = admin_login()
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['token']}"}


def order_payload():
    return {
        "customer_name": "Cliente Teste",
        "customer_email": "cliente@example.com",
        "customer_cpf": "12345678909",
        "customer_phone": "11999999999",
        "address_zip": "01001000",
        "address_street": "Praca da Se",
        "address_number": "1",
        "address_neighborhood": "Se",
        "address_city": "Sao Paulo",
        "address_state": "SP",
        "items": [{"id": 1, "quantity": 1}],
    }


def catalog_totals():
    manifest = json.loads((DEFAULT_SOURCE / "manifest.json").read_text(encoding="utf-8"))
    products = manifest.get("products") or []
    return len(products), sum(len(product.get("images") or []) for product in products)


def clear_store_setting_overrides():
    with SessionLocal() as db:
        db.query(StoreSetting).delete()
        sync_default_coupon(db)
        db.commit()
