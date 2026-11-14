"""
第四阶段 · 18 httpx + pytest — 检验练习

运行方式（在项目根目录）：

    .venv/bin/python -m pytest 4工程化/18httpx-pytest/ -v

练习 1、2 在同目录 conftest.py 里。
全部 PASSED = 18 httpx + pytest 过关 ✅
"""

import pytest


# ===== 练习 3：GET 空列表 =====
def test_list_todos_empty(client):
    """
    GET /todos
    期望：状态码 200，响应体是 []
    """
    r = client.get("/todos")
    assert r.status_code == 200
    assert r.json() == []


# ===== 练习 4：POST 创建 =====
def test_create_todo(client):
    """
    POST /todos，json={"title": "buy milk"}
    期望：
    - 状态码 201
    - body["title"] == "buy milk"
    - body["id"] == 1
    - body["done"] is False
    """
    r = client.post("/todos", json={"title": "buy milk"})
    assert r.status_code == 201

    body = r.json()
    assert body["title"] == "buy milk"
    assert body["id"] == 1
    assert body["done"] is False


# ===== 练习 5：校验失败 =====
def test_create_todo_empty_title(client):
    """
    POST /todos，json={"title": ""}
    期望：状态码 422（Pydantic 的 min_length 校验）
    """
    r = client.post("/todos", json={"title": ""})
    assert r.status_code == 422


# ===== 练习 6：不存在的资源 =====
def test_get_missing_todo(client):
    """
    GET /todos/999
    期望：状态码 404
    """
    r = client.get("/todos/999")
    assert r.status_code == 404


# ===== 练习 7：DELETE 与 204 =====
def test_delete_todo(client):
    """
    1. POST /todos 创建一条（json={"title": "to delete"}）
    2. DELETE /todos/1
       期望：状态码 204，且 r.content == b""（不能调用 r.json()）
    3. 再 GET /todos/1
       期望：状态码 404
    """
    r = client.post("/todos", json={"title": "to delete"})
    assert r.status_code == 201

    r = client.delete("/todos/1")
    assert r.status_code == 204
    assert r.content == b""

    r = client.get("/todos/1")
    assert r.status_code == 404


# ===== 练习 8：测试之间的隔离 =====
def test_isolation_a_create(client):
    """
    POST /todos 创建一条数据，断言 201。

    这条测试故意留下数据。
    """
    r = client.post("/todos", json={"title": "add todo"})
    assert r.status_code == 201


def test_isolation_b_fresh(client):
    """
    GET /todos，断言响应体是 []。

    如果 client/store fixture 没做到每个测试独立，
    这里会看到上一条测试留下的数据，测试失败。
    """
    r = client.get("/todos")
    assert r.status_code == 200
    assert r.json() == []


# ===== 练习 9：请求头认证 =====
def test_me_requires_token(client):
    """
    GET /me，不带任何请求头。
    期望：状态码 401
    """
    r = client.get("/me")
    assert r.status_code == 401


def test_me_with_token(client):
    """
    GET /me，headers={"X-Token": "secret"}
    期望：状态码 200，body == {"user": "demo-user"}
    """
    r = client.get("/me", headers={"X-Token": "secret"})
    assert r.status_code == 200
    assert r.json() == {"user": "demo-user"}


# ===== 练习 10：parametrize 状态码 =====
@pytest.mark.parametrize(
    "method, url, expected",
    [
        ("get", "/todos", 200),
        ("get", "/todos/999", 404),
        ("get", "/me", 401),
    ],
)
def test_status_codes(client, method, url, expected):
    """
    用 getattr(client, method)(url) 发请求（method 是字符串），
    断言 r.status_code == expected。
    """
    assert getattr(client, method)(url).status_code == expected
