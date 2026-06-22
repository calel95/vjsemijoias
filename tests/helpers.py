from fastapi.testclient import TestClient

from backend.app import app


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
