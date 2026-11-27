"""
第五阶段 · 23 Monolith vs Microservices — 检验练习

本章不写业务代码，把「判断架构类型 / 判断该不该拆 / 跨服务拼装」的规则落成函数。
每个函数的 TODO 需要你来实现。
写完后运行: python practice.py
全部通过 = 23 过关 ✅
"""

from typing import Callable


# ===== 练习 1：架构分类 =====
def classify_architecture(deploy_units: int, shared_database: bool) -> str:
    """
    根据部署单位数量和数据是否共享，判断架构类型。

    规则：
    - deploy_units == 1 → "monolith"
    - deploy_units > 1 且 shared_database 为 True → "distributed_monolith"
    - deploy_units > 1 且 shared_database 为 False → "microservices"

    例如:
    classify_architecture(1, True)  → "monolith"
    classify_architecture(3, False) → "microservices"
    classify_architecture(3, True)  → "distributed_monolith"
    """
    if deploy_units == 1:
        return "monolith"
    if deploy_units > 1:
        if shared_database:
            return "distributed_monolith"
        return "microservices"


# ===== 练习 2：检测「按技术层横切」 =====
def audit_split(services: list[dict]) -> list[str]:
    """
    检查服务拆分是否「按技术层横切」。

    每个 service 形如 {"name": "controller-service", "responsibility": "controller"}
    responsibility 取值: "controller" / "service" / "dao" / "business"

    只要存在 responsibility 是前三者之一的服务，就在结果里加入 "horizontal_split"
    （多个也只记一次）。没有则返回空列表。

    例如:
    audit_split([{"name": "a", "responsibility": "controller"}]) → ["horizontal_split"]
    audit_split([{"name": "auth", "responsibility": "business"}]) → []
    """
    layer_kinds = {"controller", "service", "dao"}
    if any(svc["responsibility"] in layer_kinds for svc in services):
        return ["horizontal_split"]
    return []


# ===== 练习 3：推荐演进路线 =====
def recommend(signals: dict) -> str:
    """
    根据信号推荐架构路线。

    signals 可能包含以下键（值都是 bool，缺省视为 False）：
    - code_messy: 代码混乱、模块耦合
    - deploy_blocked: 团队发版互相阻塞
    - uneven_load: 某个模块单独吃资源，需要独立扩缩容

    规则（按优先级从上到下判断）：
    1. code_messy 为 True 且 deploy_blocked、uneven_load 都为 False → "split_modules"
    2. deploy_blocked 或 uneven_load 为 True → "microservices"
    3. 其他情况 → "modular_monolith"

    例如:
    recommend({"code_messy": True}) → "split_modules"
    recommend({"code_messy": True, "deploy_blocked": True}) → "microservices"
    recommend({}) → "modular_monolith"
    """
    code_messy = signals.get("code_messy", False)
    deploy_blocked = signals.get("deploy_blocked", False)
    uneven_load = signals.get("uneven_load", False)

    if code_messy and not deploy_blocked and not uneven_load:
        return "split_modules"
    if deploy_blocked or uneven_load:
        return "microservices"
    return "modular_monolith"


# ===== 练习 4：跨服务批量拼装（分布式 N+1 的正确解法） =====
def build_owner_names(
    todo_rows: list[dict],
    fetch_users: Callable[[list[int]], dict[int, str]],
) -> list[dict]:
    """
    跨服务拼装创建者昵称。

    todo_rows: [{"id": 1, "user_id": 10}, ...]
    fetch_users: 模拟 auth-service 的批量接口，接收用户 id 列表，返回 {user_id: username}

    要求：
    - fetch_users 只能调用一次，且传入所有出现过的 user_id（去重，顺序不限）
    - todo_rows 为空时不要调用 fetch_users，直接返回 []
    - 返回 [{"id": todo_id, "username": 昵称}, ...]，顺序与 todo_rows 一致
    - 查不到的用户，username 用 "未知用户"

    例如:
    build_owner_names([{"id": 1, "user_id": 10}], lambda ids: {10: "alice"})
      → [{"id": 1, "username": "alice"}]
    """
    if not todo_rows:
        return []

    user_ids = {row["user_id"] for row in todo_rows}
    usernames = fetch_users(list(user_ids))

    return [
        {"id": row["id"], "username": usernames.get(row["user_id"], "未知用户")}
        for row in todo_rows
    ]


# ===== 练习 5：数据冗余的事后同步（最终一致） =====
def sync_username(todos: list[dict], user_id: int, new_name: str) -> int:
    """
    用户改名后，同步 todo 里冗余存着的昵称（模拟消费「用户已改名」事件）。

    todos: [{"id": 1, "user_id": 10, "owner_name": "alice"}, ...]
    把所有 user_id 匹配的 todo 的 owner_name 原地改成 new_name，返回修改的条数。

    例如:
    todos = [{"id": 1, "user_id": 10, "owner_name": "old"},
             {"id": 2, "user_id": 11, "owner_name": "bob"}]
    sync_username(todos, 10, "new") → 1
    todos[0]["owner_name"] == "new"，todos[1] 保持不变
    """
    changed = 0
    for todo in todos:
        if todo["user_id"] == user_id:
            todo["owner_name"] = new_name
            changed += 1
    return changed


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []

    def check(name: str, actual, expected):
        if actual == expected:
            print(f"✅ {name}")
        else:
            errors.append(f"❌ {name}: 期望 {expected!r}，实际 {actual!r}")

    # ---- 练习 1 ----
    check("练习1 单部署单位 = 单体",
          classify_architecture(1, True), "monolith")
    check("练习1 多部署单位 + 独立库 = 微服务",
          classify_architecture(3, False), "microservices")
    check("练习1 多部署单位 + 共用库 = 分布式单体",
          classify_architecture(3, True), "distributed_monolith")
    check("练习1 两个单位也算",
          classify_architecture(2, True), "distributed_monolith")

    # ---- 练习 2 ----
    check("练习2 单个横切层",
          audit_split([{"name": "controller-service", "responsibility": "controller"}]),
          ["horizontal_split"])
    check("练习2 多个横切层只记一次",
          audit_split([
              {"name": "controller-service", "responsibility": "controller"},
              {"name": "dao-service", "responsibility": "dao"},
          ]),
          ["horizontal_split"])
    check("练习2 按业务能力切",
          audit_split([
              {"name": "auth", "responsibility": "business"},
              {"name": "todos", "responsibility": "business"},
          ]),
          [])

    # ---- 练习 3 ----
    check("练习3 只是代码乱 → 拆模块",
          recommend({"code_messy": True}), "split_modules")
    check("练习3 代码乱 + 发版阻塞 → 微服务",
          recommend({"code_messy": True, "deploy_blocked": True}), "microservices")
    check("练习3 局部扩容压力 → 微服务",
          recommend({"uneven_load": True}), "microservices")
    check("练习3 没有信号 → 模块化单体",
          recommend({}), "modular_monolith")
    check("练习3 全部为 False → 模块化单体",
          recommend({"code_messy": False, "deploy_blocked": False, "uneven_load": False}),
          "modular_monolith")

    # ---- 练习 4 ----
    calls = []

    def fake_fetch(ids):
        calls.append(list(ids))
        return {10: "alice", 11: "bob"}

    rows = [
        {"id": 1, "user_id": 10},
        {"id": 2, "user_id": 11},
        {"id": 3, "user_id": 10},
    ]
    result = build_owner_names(rows, fake_fetch)
    check("练习4 按 todo 顺序拼装", result, [
        {"id": 1, "username": "alice"},
        {"id": 2, "username": "bob"},
        {"id": 3, "username": "alice"},
    ])
    check("练习4 只调用一次接口", len(calls), 1)
    check("练习4 传入的 id 去重", sorted(calls[0]) if calls else None, [10, 11])

    calls2 = []

    def fetch_partial(ids):
        calls2.append(list(ids))
        return {10: "alice"}

    check("练习4 查不到的用户显示未知",
          build_owner_names([{"id": 5, "user_id": 99}], fetch_partial),
          [{"id": 5, "username": "未知用户"}])

    calls3 = []

    def never_fetch(ids):
        calls3.append(ids)
        return {}

    check("练习4 空列表返回空", build_owner_names([], never_fetch), [])
    check("练习4 空列表不调用接口", len(calls3), 0)

    # ---- 练习 5 ----
    todos = [
        {"id": 1, "user_id": 10, "owner_name": "old"},
        {"id": 2, "user_id": 11, "owner_name": "bob"},
        {"id": 3, "user_id": 10, "owner_name": "old"},
    ]
    n = sync_username(todos, 10, "new")
    check("练习5 返回修改条数", n, 2)
    check("练习5 匹配项已更新、其他不动",
          [t["owner_name"] for t in todos], ["new", "bob", "new"])
    check("练习5 没有匹配返回 0", sync_username(todos, 999, "x"), 0)

    if errors:
        print(f"\n有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("\n🎉 全部通过！23 Monolith vs Microservices = ✅")
