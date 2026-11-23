"""
Task 3 · tests/test_cache.py — 缓存行为测试

把 Task 2 的 11 步手动验证自动化。
可用 fixture：client、auth / other_auth、db_session

验证「缓存命中」的经典手法：
    缓存回填后，绕过 API 直接改数据库；如果 API 还返回旧值 → 说明它读的是缓存。

运行：
    ../../.venv/bin/python -m pytest tests/test_cache.py -q
"""

from sqlalchemy import update

import cache
import models


def _create(client, auth, title="买牛奶"):
    r = client.post("/todos", json={"title": title}, headers=auth["headers"])
    assert r.status_code == 201, f"创建失败 {r.status_code} {r.text}"
    return r.json()


def _get_single(client, auth, todo_id):
    return client.get(f"/todos/{todo_id}", headers=auth["headers"])


# ===== 单条读路径 =====
def test_single_get_refills_cache(client, auth):
    todo = _create(client, auth)
    key = cache.todo_key(auth["user_id"], todo["id"])
    cache.redis_client.delete(key)      # 确保未命中

    r = _get_single(client, auth, todo["id"])

    assert r.status_code == 200
    assert cache.redis_client.exists(key) == 1, "未命中查库后没有回填缓存"
    ttl = cache.redis_client.ttl(key)
    assert 0 < ttl <= cache.TTL_TODO, f"实际 ttl={ttl}"
    assert cache.get_json(key) == r.json()   # 缓存内容 == 接口响应


def test_second_get_hits_cache(client, auth, db_session):
    todo = _create(client, auth, "缓存里的标题")
    _get_single(client, auth, todo["id"])    # 第一次：回填

    # 绕过 API 直接改库：如果 API 仍返回旧标题，说明它没查库，读的是缓存
    db_session.execute(
        update(models.Todo).where(models.Todo.id == todo["id"]).values(title="数据库里的新标题")
    )
    db_session.commit()

    r = _get_single(client, auth, todo["id"])
    assert r.json()["title"] == "缓存里的标题", "第二次 GET 没有命中缓存（竟然查了库）"


def test_list_refills_and_hits_cache(client, auth):
    key = cache.list_key(auth["user_id"])
    _create(client, auth)

    r = client.get("/todos", headers=auth["headers"])
    assert r.status_code == 200
    assert cache.get_json(key) == r.json()
    assert 0 < cache.redis_client.ttl(key) <= cache.TTL_TODO


def test_empty_list_is_cached(client, auth):
    # 空列表 [] 是 falsy —— 必须仍然被当成「有缓存」，否则每次都穿透
    key = cache.list_key(auth["user_id"])

    r = client.get("/todos", headers=auth["headers"])
    assert r.json() == []
    assert cache.get_json(key) == [], "空列表没有被缓存"
    assert cache.redis_client.exists(key) == 1


# ===== 写路径删缓存 =====
def test_patch_invalidates_both_keys(client, auth):
    todo = _create(client, auth, "原标题")
    single = cache.todo_key(auth["user_id"], todo["id"])
    lst = cache.list_key(auth["user_id"])
    _get_single(client, auth, todo["id"])                  # 填单条缓存
    client.get("/todos", headers=auth["headers"])          # 填列表缓存
    assert cache.redis_client.exists(single, lst) == 2

    r = client.patch(f"/todos/{todo['id']}", json={"title": "新标题"}, headers=auth["headers"])
    assert r.status_code == 200

    assert cache.redis_client.exists(single) == 0, "PATCH 后单条缓存没删"
    assert cache.redis_client.exists(lst) == 0, "PATCH 后列表缓存没删"

    # 重新读取拿到的是新值
    assert _get_single(client, auth, todo["id"]).json()["title"] == "新标题"
    assert client.get("/todos", headers=auth["headers"]).json()[0]["title"] == "新标题"


def test_delete_invalidates_both_keys(client, auth):
    todo = _create(client, auth)
    single = cache.todo_key(auth["user_id"], todo["id"])
    lst = cache.list_key(auth["user_id"])
    _get_single(client, auth, todo["id"])
    client.get("/todos", headers=auth["headers"])
    assert cache.redis_client.exists(single, lst) == 2

    r = client.delete(f"/todos/{todo['id']}", headers=auth["headers"])
    assert r.status_code == 204

    assert cache.redis_client.exists(single) == 0, "DELETE 后单条缓存没删（幽灵 todo）"
    assert cache.redis_client.exists(lst) == 0, "DELETE 后列表缓存没删"


def test_create_invalidates_list_cache(client, auth):
    client.get("/todos", headers=auth["headers"])          # 先缓存一个空列表
    assert cache.redis_client.exists(cache.list_key(auth["user_id"])) == 1

    _create(client, auth, "新加的")
    assert cache.redis_client.exists(cache.list_key(auth["user_id"])) == 0

    titles = [t["title"] for t in client.get("/todos", headers=auth["headers"]).json()]
    assert titles == ["新加的"]


# ===== 哨兵 =====
def test_missing_todo_writes_sentinel(client, auth):
    key = cache.todo_key(auth["user_id"], 999999)

    r = _get_single(client, auth, 999999)
    assert r.status_code == 404

    assert cache.redis_client.exists(key) == 1, "查不到时没有写哨兵"
    assert cache.redis_client.get(key) == "null"          # 存的是 JSON null
    assert cache.get_json(key) is None                    # 读出来是 None（哨兵命中）
    ttl = cache.redis_client.ttl(key)
    assert 0 < ttl <= cache.TTL_MISSING, f"实际 ttl={ttl}"

    # 第二次仍是 404（命中哨兵，没查库）
    assert _get_single(client, auth, 999999).status_code == 404


def test_other_users_todo_writes_sentinel_for_self(client, auth, other_auth):
    # A 看 B 的 todo → 404，并且哨兵写在 A 自己的 key 空间里
    theirs = _create(client, other_auth, "B 的")
    key = cache.todo_key(auth["user_id"], theirs["id"])

    r = _get_single(client, auth, theirs["id"])
    assert r.status_code == 404
    assert cache.get_json(key) is None
