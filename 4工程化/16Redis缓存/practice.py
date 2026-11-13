"""
第四阶段 · 16 Redis 缓存 — 检验练习

每个函数的 TODO 需要你来实现。
写完后运行: .venv/bin/python 4工程化/16Redis缓存/practice.py
全部通过 = 16 Redis 缓存 过关 ✅

前置条件：Redis 服务已启动（redis-cli ping 返回 PONG）。
练习统一使用 db=15，避免污染其他库的数据。
"""

import json

import redis

# 模拟数据库（真实项目里这层是 PostgreSQL）
FAKE_DB = {
    1: {"id": 1, "title": "买菜", "done": False},
    2: {"id": 2, "title": "写周报", "done": True},
    3: {"id": 3, "title": "健身", "done": False},
}


# ===== 练习 1：建立连接 =====
def get_client(host="localhost", port=6379, db=15):
    """
    返回一个 redis-py 客户端。

    要求：
    - 默认连接 localhost:6379 的 15 号库
    - decode_responses=True（读出来是 str 而不是 bytes）

    例如: get_client().ping() → True
    """
    return redis.Redis(host=host, port=port, db=db, decode_responses=True)


# ===== 练习 2：带 TTL 的写入 =====
def set_with_ttl(client, key, value, seconds):
    """
    写入一个字符串，并设置过期时间（秒）。

    例如: set_with_ttl(r, "greet", "你好", 100)
          r.get("greet") → "你好"
    """
    client.set(key, value, ex=seconds)


def get_ttl(client, key):
    """
    返回 key 的剩余寿命（秒）。
    永不过期返回 -1，key 不存在返回 -2（这两个值由 Redis 直接给出）。

    例如: get_ttl(r, "greet") → 98
    """
    return client.ttl(key)


# ===== 练习 3：Cache-Aside 读 =====
def get_todo_cached(client, todo_id):
    """
    Cache-Aside 读：先查缓存，未命中再查 FAKE_DB，查到后回填缓存。

    缓存 key 格式：f"todo:{todo_id}"
    缓存有效期：60 秒
    缓存内容：用 json.dumps 序列化的 todo 字典
    FAKE_DB 里没有该 id 时，返回 None，且不写缓存

    例如: 第一次调用 get_todo_cached(r, 1) → 查 FAKE_DB
          第二次调用（60 秒内）    → 直接读缓存，不碰 FAKE_DB
    """
    key = f"todo:{todo_id}"
    todo = client.get(key)
    if todo is None:
        todo = FAKE_DB.get(todo_id)
        if todo is not None:
            client.set(key, json.dumps(todo), ex=60)
            return todo
        return None
    return json.loads(todo)


# ===== 练习 4：写时删缓存 =====
def update_todo(client, todo_id, new_title):
    """
    先更新 FAKE_DB，再删除对应缓存（先更新库，再删缓存）。

    缓存 key 格式：f"todo:{todo_id}"
    FAKE_DB 里没有该 id 时，直接返回，不做任何操作。

    例如: update_todo(r, 1, "买水果")
          get_todo_cached(r, 1) → 标题是 "买水果"
    """
    key = f"todo:{todo_id}"
    todo = FAKE_DB.get(todo_id)

    if todo is None:
        return
    todo["title"] = new_title
    client.delete(key)


# ===== 练习 5：缓存穿透防护 =====
def get_todo_cached_v2(client, todo_id):
    """
    在 Cache-Aside 的基础上，防「缓存穿透」：
    FAKE_DB 里也不存在的 id，缓存一个哨兵值 "__missing__"（30 秒），
    避免每次查询都穿透到数据库。

    行为：
    - 缓存命中哨兵值 → 返回 None
    - 缓存未命中且 FAKE_DB 有数据 → 回填 json 并返回 dict
    - 缓存未命中且 FAKE_DB 没数据 → 写哨兵值 "__missing__"，返回 None

    例如: get_todo_cached_v2(r, 999) → None，且 r.get("todo:999") == "__missing__"
    """
    key = f"todo:{todo_id}"
    todo = client.get(key)

    if todo == "__missing__":
        return None

    if todo is None:
        todo = FAKE_DB.get(todo_id)
        if todo is None:
            client.set(key, "__missing__", ex=30)
        else:
            client.set(key, json.dumps(todo), ex=60)
        return todo

    return json.loads(todo)


# ===== 练习 6：Hash 存对象 =====
def save_user_hash(client, user_id, data):
    """
    用 Redis Hash 存一个用户对象。
    key 格式：f"user:{user_id}"
    把 data 的每个键值对都存进 hash。

    例如: save_user_hash(r, 1, {"name": "阿波", "age": 30})
          r.hgetall("user:1") → {"name": "阿波", "age": "30"}
    """
    key = f"user:{user_id}"
    client.hset(key, mapping=data)


def load_user_hash(client, user_id):
    """
    读回 Hash 中的所有字段。
    key 不存在时返回空字典 {}。

    例如: load_user_hash(r, 1) → {"name": "阿波", "age": "30"}
    """
    key = f"user:{user_id}"
    return client.hgetall(key)


# ===== 练习 7：Sorted Set 排行榜 =====
def add_score(client, name, score):
    """
    向排行榜 "leaderboard" 写入（或更新）一个成员及其分数。

    例如: add_score(r, "alice", 100)
    """
    key = "leaderboard"
    client.zadd(key, mapping={name: score})


def top3(client):
    """
    返回排行榜前 3 名的成员名（按分数从高到低）。

    例如: top3(r) → ["bob", "carol", "alice"]
    """
    key = "leaderboard"
    return client.zrevrange(key, 0, 2)


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []

    r = redis.Redis(host="localhost", port=6379, db=15, decode_responses=True)
    try:
        r.ping()
    except redis.ConnectionError:
        print("❌ 连不上 Redis，先确认 redis-cli ping 返回 PONG")
        raise SystemExit(1)

    r.flushdb()

    # ----- 练习 1 -----
    try:
        c = get_client()
        if c is None:
            errors.append("练习1: get_client 返回了 None")
        elif not c.ping():
            errors.append("练习1: 连接不通")
        elif c.connection_pool.connection_kwargs.get("decode_responses") is not True:
            errors.append("练习1: 没开 decode_responses=True")
    except Exception as e:
        errors.append(f"练习1: 报错 {type(e).__name__}: {e}")

    # ----- 练习 2 -----
    try:
        set_with_ttl(r, "greet", "你好", 100)
        v = r.get("greet")
        if v != "你好":
            errors.append(f"练习2: set_with_ttl 后 get 期望 '你好'，实际 {v!r}")

        remain = get_ttl(r, "greet")
        if not (isinstance(remain, int) and 90 <= remain <= 100):
            errors.append(f"练习2: get_ttl 期望 90~100 的整数，实际 {remain!r}")

        r.set("noexpire", "x")
        if get_ttl(r, "noexpire") != -1:
            errors.append(f"练习2: 无过期 key 的 ttl 期望 -1，实际 {get_ttl(r, 'noexpire')!r}")
    except Exception as e:
        errors.append(f"练习2: 报错 {type(e).__name__}: {e}")

    # ----- 练习 3 -----
    try:
        r.delete("todo:1")
        first = get_todo_cached(r, 1)
        if first != {"id": 1, "title": "买菜", "done": False}:
            errors.append(f"练习3: 首次读取期望 FAKE_DB[1]，实际 {first!r}")
        if not r.exists("todo:1"):
            errors.append("练习3: 首次读取后没回填缓存")

        FAKE_DB[1]["title"] = "库里临时改的"
        second = get_todo_cached(r, 1)
        if second is None or second.get("title") != "买菜":
            errors.append(f"练习3: 缓存期内应返回缓存旧值 '买菜'，实际 {second!r}")

        r.delete("todo:1")
        third = get_todo_cached(r, 1)
        if third is None or third.get("title") != "库里临时改的":
            errors.append(f"练习3: 删缓存后应读到新值 '库里临时改的'，实际 {third!r}")

        FAKE_DB[1]["title"] = "买菜"
    except Exception as e:
        errors.append(f"练习3: 报错 {type(e).__name__}: {e}")

    # ----- 练习 4 -----
    try:
        r.delete("todo:2")
        get_todo_cached(r, 2)
        if not r.exists("todo:2"):
            errors.append("练习4: 前置失败——缓存没预热成功")

        update_todo(r, 2, "改好的周报")
        if FAKE_DB[2]["title"] != "改好的周报":
            errors.append(f"练习4: FAKE_DB 没更新，实际 {FAKE_DB[2]!r}")
        if r.exists("todo:2"):
            errors.append("练习4: 更新后缓存没删除")

        again = get_todo_cached(r, 2)
        if again is None or again.get("title") != "改好的周报":
            errors.append(f"练习4: 删缓存后应读回新值，实际 {again!r}")

        # 不存在的 id 不应报错
        update_todo(r, 999, "不存在")
        FAKE_DB[2]["title"] = "写周报"
    except Exception as e:
        errors.append(f"练习4: 报错 {type(e).__name__}: {e}")

    # ----- 练习 5 -----
    try:
        r.delete("todo:999")
        res = get_todo_cached_v2(r, 999)
        if res is not None:
            errors.append(f"练习5: 不存在的 id 期望 None，实际 {res!r}")
        if r.get("todo:999") != "__missing__":
            errors.append(f"练习5: 期望缓存哨兵 '__missing__'，实际 {r.get('todo:999')!r}")
        cache_ttl = r.ttl("todo:999")
        if not (0 < cache_ttl <= 30):
            errors.append(f"练习5: 哨兵 TTL 期望 0~30，实际 {cache_ttl!r}")

        r.delete("todo:3")
        got = get_todo_cached_v2(r, 3)
        if got is None or got.get("title") != "健身":
            errors.append(f"练习5: 存在的 id 应返回 dict，实际 {got!r}")
    except Exception as e:
        errors.append(f"练习5: 报错 {type(e).__name__}: {e}")

    # ----- 练习 6 -----
    try:
        r.delete("user:7")
        save_user_hash(r, 7, {"name": "阿波", "age": 30})
        raw = r.hgetall("user:7")
        if raw != {"name": "阿波", "age": "30"}:
            errors.append(f"练习6: hgetall 期望 name/age 两个字段，实际 {raw!r}")

        loaded = load_user_hash(r, 7)
        if loaded != {"name": "阿波", "age": "30"}:
            errors.append(f"练习6: load_user_hash 期望完整字段，实际 {loaded!r}")

        if load_user_hash(r, 123456) != {}:
            errors.append(f"练习6: 不存在的 user 期望 {{}}，实际 {load_user_hash(r, 123456)!r}")
    except Exception as e:
        errors.append(f"练习6: 报错 {type(e).__name__}: {e}")

    # ----- 练习 7 -----
    try:
        r.delete("leaderboard")
        add_score(r, "alice", 100)
        add_score(r, "bob", 85)
        add_score(r, "carol", 120)
        add_score(r, "bob", 150)  # 更新分数

        got = top3(r)
        if got != ["bob", "carol", "alice"]:
            errors.append(f"练习7: top3 期望 ['bob', 'carol', 'alice']，实际 {got!r}")
    except Exception as e:
        errors.append(f"练习7: 报错 {type(e).__name__}: {e}")

    # ----- 汇总 -----
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！16 Redis 缓存 = ✅")
