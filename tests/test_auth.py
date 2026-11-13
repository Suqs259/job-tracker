import pytest


def test_protected_api_rejects_anonymous(client):
    response = client.get("/api/applications")
    assert response.status_code == 401
    assert "未登录" in response.get_json()["error"]


def test_page_redirects_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_status_endpoint_reports_uninitialized(client):
    data = client.get("/api/auth/status").get_json()
    assert data == {"initialized": False, "logged_in": False, "username": None}


def test_register_creates_account_and_session(client):
    response = client.post("/api/auth/register", json={"username": "tester", "password": "secret123"})
    assert response.status_code == 201
    assert response.get_json()["username"] == "tester"

    status = client.get("/api/auth/status").get_json()
    assert status["initialized"] is True
    assert status["logged_in"] is True

    # 注册后可直接访问受保护接口
    assert client.get("/api/applications").status_code == 200


def test_register_rejects_second_account(client):
    client.post("/api/auth/register", json={"username": "tester", "password": "secret123"})
    response = client.post("/api/auth/register", json={"username": "other", "password": "secret123"})
    assert response.status_code == 403


@pytest.mark.parametrize("payload, expected", [
    ({"username": "ab", "password": "secret123"}, "用户名长度"),
    ({"username": "tester", "password": "123"}, "密码至少"),
    ({}, "用户名长度"),
])
def test_register_validates_input(client, payload, expected):
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert expected in response.get_json()["error"]


def test_login_with_correct_password(client):
    client.post("/api/auth/register", json={"username": "tester", "password": "secret123"})
    client.post("/api/auth/logout")

    assert client.get("/api/applications").status_code == 401

    response = client.post("/api/auth/login", json={"username": "tester", "password": "secret123"})
    assert response.status_code == 200
    assert client.get("/api/applications").status_code == 200


def test_login_rejects_wrong_password(client):
    client.post("/api/auth/register", json={"username": "tester", "password": "secret123"})
    client.post("/api/auth/logout")

    response = client.post("/api/auth/login", json={"username": "tester", "password": "wrong-pass"})
    assert response.status_code == 401
    # 不区分账号不存在与密码错误
    assert response.get_json()["error"] == "用户名或密码错误"


def test_logout_clears_session(auth_client):
    assert auth_client.post("/api/auth/logout").status_code == 204
    assert auth_client.get("/api/applications").status_code == 401


def test_login_page_renders(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "登录" in response.get_data(as_text=True)
