"""
第四阶段 · 阶段项目 · Task 2 — cache.py
Redis 缓存层：只负责「存取 JSON」，不碰数据库、不碰 FastAPI。

key 设计（user_id 写进 key = 命中即已授权，不可能漏掉所有权检查）：
    todo:{user_id}:{todo_id}     单条，例 todo:7:42
    todos:user:{user_id}         列表，例 todos:user:7

读缓存的三种结果（get_json 的返回值）：
    CACHE_MISS   → Redis 里没有这个 key       → 调用方去查库
    None         → key 存在，值是 null（哨兵）→ 调用方直接 404
    dict / list  → 命中                        → 调用方直接返回

写路径的顺序（学习项 16）：
    先 db.commit()，再删缓存。反了会让「未命中 → 查库（旧值）→ 回填」跑在 commit 之前。

写完后运行: ../../.venv/bin/python cache.py
全部通过 = Task 2 的 cache.py 部分 ✅
"""

import json

import redis

import config

# ===== 配置 =====
TTL_TODO = 300        # 单条 / 列表缓存：5 分钟
TTL_MISSING = 60      # 哨兵：1 分钟（确认过不存在）

# 「没有这个 key」的独立标记。
# 不能和 None 混用 —— None 是哨兵（确认过不存在），CACHE_MISS 是「没查过」。
CACHE_MISS = object()

redis_client = redis.Redis.from_url(config.REDIS_URL, decode_responses=True)


# ===== key 构造 =====
def todo_key(user_id: int, todo_id: int) -> str:
    """
    单条 todo 的缓存 key。

    todo_key(7, 42) -> "todo:7:42"
    """
    return f"todo:{user_id}:{todo_id}"


def list_key(user_id: int) -> str:
    """
    某个用户的 todo 列表缓存 key。

    list_key(7) -> "todos:user:7"
    """
    return f"todos:user:{user_id}"


# ===== JSON 读写 =====
def get_json(key: str):
    """
    读缓存，返回值有三种可能：
      CACHE_MISS  → Redis 里没有这个 key
      None        → key 存在，但值是 JSON null（哨兵：确认过不存在）
      dict / list → 正常数据

    提示：redis_client.get(key) 在 key 不存在时返回 None（字符串形式的 "null"
    会返回字符串 "null"，不会混淆）。
    """
    val = redis_client.get(key)

    if val is None: # 没有这个key
        return CACHE_MISS
    if val == "null": # 当前是哨兵, json.loads("null") == None
        return None
    return json.loads(val)


def set_json(key: str, value, ttl: int | None = None) -> None:
    """
    把任意可 JSON 序列化的值写进 Redis，并设置过期时间。

    - ttl 为 None 时用 TTL_TODO；
    - value 传 None 就是写哨兵（存进去是字符串 "null"，读出来是 None）；
    - 提示：redis_client.set(name, value, ex=秒)。
    """
    if ttl is None:
        ttl = TTL_TODO
    redis_client.set(key, json.dumps(value), ex=ttl)


def delete(*keys: str) -> int:
    """
    删除一个或多个 key，返回实际删掉的个数。

    delete("todo:7:42")
    delete("todo:7:42", "todos:user:7")   # 一次删多个
    """
    return redis_client.delete(*keys)


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    from uuid import uuid4

    errors = []
    prefix = f"test:{uuid4().hex[:8]}"
    k1, k2, k3, k4 = (f"{prefix}:{i}" for i in range(4))

    def check(name, cond, detail=""):
        if cond:
            print(f"✅ {name}")
        else:
            errors.append(f"{name} {detail}")

    try:
        # ---------- key 构造 ----------
        check("todo_key(7, 42) == 'todo:7:42'",
              todo_key(7, 42) == "todo:7:42", f"实际 {todo_key(7, 42)!r}")
        check("list_key(7) == 'todos:user:7'",
              list_key(7) == "todos:user:7", f"实际 {list_key(7)!r}")

        # ---------- 未命中 ----------
        redis_client.delete(k1)
        check("没有 key → CACHE_MISS", get_json(k1) is CACHE_MISS,
              f"实际 {get_json(k1)!r}")

        # ---------- 正常数据往返 ----------
        data = {"id": 42, "title": "买牛奶", "done": False, "user_id": 7}
        set_json(k1, data, ttl=120)
        got = get_json(k1)
        check("写入 dict 后能原样读回", got == data, f"实际 {got!r}")
        check("写入后带 TTL", 0 < redis_client.ttl(k1) <= 120,
              f"实际 ttl={redis_client.ttl(k1)}")

        # ---------- 哨兵 vs 未命中 ----------
        set_json(k2, None, ttl=TTL_MISSING)
        check("哨兵（None）命中返回 None，不是 CACHE_MISS",
              get_json(k2) is None, f"实际 {get_json(k2)!r}")
        check("哨兵 key 确实存在", redis_client.exists(k2) == 1)

        # ---------- 列表往返 ----------
        set_json(k3, [{"id": 1}, {"id": 2}])
        check("写入 list 后能原样读回", get_json(k3) == [{"id": 1}, {"id": 2}],
              f"实际 {get_json(k3)!r}")
        check("默认 TTL 是 TTL_TODO",
              0 < redis_client.ttl(k3) <= TTL_TODO, f"实际 {redis_client.ttl(k3)}")

        # ---------- 删除多个 ----------
        set_json(k1, {"x": 1})
        set_json(k4, {"y": 2})
        removed = delete(k1, k3, k4)
        check("delete 返回删除个数 3", removed == 3, f"实际 {removed!r}")
        check("删除后三个 key 都是 CACHE_MISS",
              all(get_json(k) is CACHE_MISS for k in (k1, k3, k4)))
        check("删除时别的 key 不受影响（k2 还在）", get_json(k2) is None)
    finally:
        redis_client.delete(k1, k2, k3, k4)

    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！Task 2 cache.py = ✅")
