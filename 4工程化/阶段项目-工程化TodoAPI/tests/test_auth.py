"""
Task 3 · tests/test_auth.py — 认证相关测试

覆盖：注册 / 登录 / 刷新 / 未认证访问
可用 fixture：client、auth / other_auth（见 conftest.py）

运行：
    ../../.venv/bin/python -m pytest tests/test_auth.py -q
"""

from uuid import uuid4

PASSWORD = "pass12345"


def _unique_username(prefix: str = "user") -> str:
    return f"{prefix}_{uuid4().hex[:8]}"


# ===== 注册 =====
def test_register_success(client):
    username = _unique_username()
    r = client.post("/auth/register", json={"username": username, "password": PASSWORD})

    assert r.status_code == 201, f"实际 {r.status_code} {r.text}"
    body = r.json()
    assert isinstance(body["id"], int)
    assert body["username"] == username
    # 密码和哈希都不能出现在响应里
    assert "password" not in body and "password_hash" not in body, f"实际字段 {list(body)}"


def test_register_duplicate_username(client):
    username = _unique_username()
    first = client.post("/auth/register", json={"username": username, "password": PASSWORD})
    assert first.status_code == 201, f"首次注册失败 {first.status_code} {first.text}"

    second = client.post("/auth/register", json={"username": username, "password": PASSWORD})
    assert second.status_code == 409, f"实际 {second.status_code} {second.text}"


def test_register_short_password(client):
    # 短密码是 Pydantic 校验层拦的 → 422，不是认证失败 401
    r = client.post("/auth/register", json={"username": _unique_username(), "password": "short"})
    assert r.status_code == 422, f"实际 {r.status_code} {r.text}"


# ===== 登录 =====
def test_login_success(client, auth):
    # 登录收 form（data=），不是 JSON（json=）
    r = client.post("/auth/login", data={"username": auth["username"], "password": PASSWORD})

    assert r.status_code == 200, f"实际 {r.status_code} {r.text}"
    body = r.json()
    assert isinstance(body["access_token"], str)
    assert isinstance(body["refresh_token"], str)
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client, auth):
    r = client.post("/auth/login", data={"username": auth["username"], "password": "wrongpass"})

    assert r.status_code == 401, f"实际 {r.status_code} {r.text}"
    # HTTP 规范：401 必须带 WWW-Authenticate
    assert r.headers.get("www-authenticate") == "Bearer"


def test_login_unknown_user_same_error(client):
    # 用户不存在和密码错误给同一提示，不泄露「这个用户名存在」
    r = client.post("/auth/login", data={"username": _unique_username("nobody"), "password": PASSWORD})
    assert r.status_code == 401


# ===== 刷新 =====
def test_refresh_token(client, auth):
    login = client.post("/auth/login", data={"username": auth["username"], "password": PASSWORD})
    tokens = login.json()

    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200, f"实际 {r.status_code} {r.text}"
    body = r.json()
    assert isinstance(body["access_token"], str)
    assert isinstance(body["refresh_token"], str)


def test_refresh_rejects_access_token(client, auth):
    # 用 access 冒充 refresh → type 校验拦下
    login = client.post("/auth/login", data={"username": auth["username"], "password": PASSWORD})
    tokens = login.json()

    r = client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401, f"实际 {r.status_code} {r.text}"


# ===== 未认证访问 =====
def test_protected_routes_without_token(client):
    r = client.get("/todos")
    assert r.status_code == 401, f"实际 {r.status_code}"
    assert r.headers.get("www-authenticate") == "Bearer"

    r = client.post("/todos", json={"title": "x"})
    assert r.status_code == 401, f"实际 {r.status_code}"
    assert r.headers.get("www-authenticate") == "Bearer"
