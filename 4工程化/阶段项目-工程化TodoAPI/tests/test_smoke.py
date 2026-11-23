"""
Task 3 · 地基自检（smoke test）
只验证 conftest 的 fixture 能用，不测业务。
"""


def test_未登录访问_todos_返回_401(client):
    r = client.get("/todos")
    assert r.status_code == 401


def test_auth_fixture_能拿到有效_token(client, auth):
    r = client.get("/users/me", headers=auth["headers"])
    assert r.status_code == 200
    assert r.json()["username"] == auth["username"]
    assert r.json()["id"] == auth["user_id"]


def test_测试之间数据隔离_a_创建(client, auth):
    r = client.post("/todos", json={"title": "隔离测试"}, headers=auth["headers"])
    assert r.status_code == 201


def test_测试之间数据隔离_b_看不到上一条(client, auth):
    r = client.get("/todos", headers=auth["headers"])
    assert r.status_code == 200
    assert r.json() == []      # 上一个测试创建的 todo 已被 clean_data 清掉
