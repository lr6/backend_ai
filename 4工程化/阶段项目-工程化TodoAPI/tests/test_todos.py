"""
Task 3 · tests/test_todos.py — Todo CRUD + 所有权（IDOR）

可用 fixture：client、auth / other_auth、db_session

运行：
    ../../.venv/bin/python -m pytest tests/test_todos.py -q
"""


def _create(client, auth, title="买牛奶"):
    r = client.post("/todos", json={"title": title}, headers=auth["headers"])
    assert r.status_code == 201, f"创建失败 {r.status_code} {r.text}"
    return r.json()


# ===== 创建 =====
def test_create_todo(client, auth):
    todo = _create(client, auth)

    assert todo["title"] == "买牛奶"
    assert todo["done"] is False
    assert todo["user_id"] == auth["user_id"]


def test_create_ignores_forged_user_id(client, auth, other_auth):
    # 请求体里塞别人的 user_id 也不能生效 —— 身份只从 token 来
    r = client.post(
        "/todos",
        json={"title": "伪造归属", "user_id": other_auth["user_id"]},
        headers=auth["headers"],
    )
    assert r.status_code == 201, f"实际 {r.status_code} {r.text}"
    assert r.json()["user_id"] == auth["user_id"]


# ===== 查询 =====
def test_list_only_own_todos(client, auth, other_auth):
    mine = _create(client, auth, "我的")
    r = client.post("/todos", json={"title": "B 的"}, headers=other_auth["headers"])
    assert r.status_code == 201

    r = client.get("/todos", headers=auth["headers"])
    assert r.status_code == 200
    assert [t["id"] for t in r.json()] == [mine["id"]]


def test_get_todo(client, auth):
    todo = _create(client, auth)
    r = client.get(f"/todos/{todo['id']}", headers=auth["headers"])

    assert r.status_code == 200
    assert r.json() == todo


def test_get_missing_todo_404(client, auth):
    r = client.get("/todos/999999", headers=auth["headers"])
    assert r.status_code == 404


# ===== 更新 =====
def test_update_partial(client, auth):
    # 只传 done → title 不能被清空（exclude_unset 的作用）
    todo = _create(client, auth, "原标题")
    r = client.patch(f"/todos/{todo['id']}", json={"done": True}, headers=auth["headers"])

    assert r.status_code == 200, f"实际 {r.status_code} {r.text}"
    body = r.json()
    assert body["done"] is True
    assert body["title"] == "原标题"


def test_update_done_false(client, auth):
    # 传 False 必须生效 —— 「传了 False」和「没传」不是一回事
    todo = _create(client, auth)
    client.patch(f"/todos/{todo['id']}", json={"done": True}, headers=auth["headers"])
    r = client.patch(f"/todos/{todo['id']}", json={"done": False}, headers=auth["headers"])

    assert r.json()["done"] is False


# ===== 删除 =====
def test_delete_todo(client, auth):
    todo = _create(client, auth)
    r = client.delete(f"/todos/{todo['id']}", headers=auth["headers"])

    assert r.status_code == 204
    assert r.content == b""          # 204 不能带 body

    r = client.get(f"/todos/{todo['id']}", headers=auth["headers"])
    assert r.status_code == 404


def test_delete_missing_todo_404(client, auth):
    r = client.delete("/todos/999999", headers=auth["headers"])
    assert r.status_code == 404


# ===== 所有权 / IDOR =====
def test_idor_read_update_delete(client, auth, other_auth):
    theirs = _create(client, other_auth, "B 的待办")

    # A 读 / 改 / 删 B 的 todo → 全部 404（不是 403，不泄露存在性）
    assert client.get(f"/todos/{theirs['id']}", headers=auth["headers"]).status_code == 404
    assert client.patch(f"/todos/{theirs['id']}", json={"done": True}, headers=auth["headers"]).status_code == 404
    assert client.delete(f"/todos/{theirs['id']}", headers=auth["headers"]).status_code == 404

    # B 的数据必须原封不动
    r = client.get(f"/todos/{theirs['id']}", headers=other_auth["headers"])
    assert r.status_code == 200
    assert r.json()["title"] == "B 的待办"
    assert r.json()["done"] is False
