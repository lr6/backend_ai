"""
第二阶段 · 学习项 10 N+1 Problem — 检验练习

本节的考点不是「能不能查出数据」，而是「**查了几条 SQL**」。
所以每道题的断言都是两件事：结果对不对 + SQL 条数对不对。

运行： .venv/bin/python 2数据持久化/10N+1Problem/practice.py
全部通过 = 学习项 10 过关 ✅

概念速记：
- relationship() 默认 lazy="select" —— 不主动查，你访问 user.todos 的那一刻才发 SQL
- N+1 = 1 条主查询 + N 条子查询（for 循环里挨个访问关联属性造成）
- selectinload(User.todos) —— 2 条 SQL，第 2 条用 WHERE user_id IN (...)，用于「一对多」
- joinedload(User.todos)   —— 1 条 SQL，用 LEFT OUTER JOIN，用于「多对一 / 一对一」
- joinedload 加载集合时记得 .unique()
"""

from contextlib import contextmanager

from sqlalchemy import create_engine, select, ForeignKey, func, event
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, Session,
    selectinload, joinedload,
)

# ============================================
# 第一部分：基础设施（已写好，别改）
# ============================================
DBURL = "postgresql+psycopg:///n1_practice_db"
engine = create_engine(DBURL)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    todos: Mapped[list["Todo"]] = relationship(back_populates="user")


class Todo(Base):
    __tablename__ = "todos"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="todos")


# ---- SQL 计数器：挂钩子，把真实执行的 SQL 一条条抓下来 ----
_caught: list[str] = []


@event.listens_for(engine, "before_cursor_execute")
def _collect(conn, cursor, statement, parameters, context, executemany):
    if not statement.startswith(("BEGIN", "ROLLBACK", "COMMIT")):
        _caught.append(" ".join(statement.split()))


@contextmanager
def track_sql():
    """用法：
        with track_sql() as sqls:
            ...随便跑查询...
        print(len(sqls), sqls)   # 本次跑了几条、都是什么
    """
    _caught.clear()
    yield _caught


def run_counting(fn, *args):
    """执行 fn(*args)，返回 (结果, 本次 SQL 条数)。测试代码用它。"""
    with track_sql() as sqls:
        result = fn(*args)
    return result, len(sqls)


def seed():
    """清空重建表 + 写入测试数据：3 个用户，每人 3 个 todo。"""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        for name in ["小明", "小红", "小刚"]:
            s.add(User(name=name, todos=[
                Todo(title=f"{name}的任务{i}") for i in range(1, 4)
            ]))
        s.commit()


# 期望的结果（测试用它跟你写的实现比对）
EXPECTED_TITLES = {
    "小明": ["小明的任务1", "小明的任务2", "小明的任务3"],
    "小红": ["小红的任务1", "小红的任务2", "小红的任务3"],
    "小刚": ["小刚的任务1", "小刚的任务2", "小刚的任务3"],
}


# ============================================
# 练习 1：证明「懒加载不会主动触发」
# ============================================
def get_all_user_names(session):
    """
    返回所有用户的名字，list[str]。

    要求：SQL 只能发 **1 条**（只查 users 表）。
    这是一个「反证」—— 说明只要你**不碰** session 里对象的 .todos，
    懒加载就不会发任何多余 SQL。所以懒加载本身不是罪。

    例如: 输入一个 Session → ["小明", "小红", "小刚"]（顺序不限）
    """
    # TODO: select(User) 查出所有用户，然后只取 .name
    users = session.scalars(select(User)).all()
    return [u.name for u in users]


# ============================================
# 练习 2：亲手复现 N+1
# ============================================
def get_users_with_todos_naive(session):
    """
    返回 dict[str, list[str]]：{用户名: [他的 todo 标题...]}，标题按原顺序。

    要求：**故意用最朴素的写法** —— 查出用户后 for 循环里直接访问
    u.todos，让 N+1 真实发生。本练习断言 SQL 条数 == **1 + 用户数**。

    这个练习是让你「签字画押」：亲眼确认朴素写法真的会发 1+N 条。

    例如: → {"小明": ["小明的任务1", ...], "小红": [...], "小刚": [...]}
    """
    # TODO: 用 session.scalars(select(User)).all() 拿用户
    #       然后列表/字典推导里访问 u.todos（这里会触发 N 条 SQL）
    users = session.scalars(select(User)).all()
    result = {}
    for u in users:
        result[u.name] = [t.title for t in u.todos]
    return result


# ============================================
# 练习 3：用 selectinload 修好（一对多）
# ============================================
def get_users_with_todos_selectin(session):
    """
    和练习 2 **完全一样的结果**，但 SQL 必须是 **2 条**。

    提示：
      - select(User).options(...)  ← 预加载写在 .options() 里
      - 从 sqlalchemy.orm 导入 selectinload
    """
    # TODO
    users = session.scalars(select(User).options(selectinload(User.todos))).all()
    result = {}
    for u in users:
        result[u.name] = [t.title for t in u.todos]
    return result


# ============================================
# 练习 4：用 joinedload 修好（一对多）
# ============================================
def get_users_with_todos_joined(session):
    """
    和练习 2 **完全一样的结果**，但 SQL 必须是 **1 条**。

    提示：
      - 换成 joinedload
      - 加载「集合」时，取结果要 .unique()，否则会报错/重复
        写法形如: session.scalars(stmt).unique().all()
    """
    # TODO
    users = session.scalars(select(User).options(joinedload(User.todos))).unique().all()
    result = {}
    for u in users:
        result[u.name] = [t.title for t in u.todos]
    return result


# ============================================
# 练习 5：反方向 —— 多对一用 joinedload 才是正解
# ============================================
def get_todos_with_user_joined(session):
    """
    反过来查：返回 list[tuple[str, str]]，每个元素是 (todo标题, 用户名)。

    要求：SQL == **1 条**。
    这里是「多对一」（很多 Todo 指向同一个 User），用 joinedload 不会放大行数。
    注意：这种方向**不需要** .unique()。

    例如: → [("小明的任务1", "小明"), ("小明的任务2", "小明"), ...]
    """
    # TODO: select(Todo).options(joinedload(Todo.user))
    todos = session.scalars(select(Todo).options(joinedload(Todo.user))).all()
    return [(t.title, t.user.name) for t in todos]


# ============================================
# 练习 6：根本不需要对象时 —— 用聚合，不用预加载
# ============================================
def count_todos_per_user(session):
    """
    返回 dict[str, int]：{用户名: 他的 todo 个数}。

    要求：SQL == **1 条**，并且**不许访问 u.todos**（不许把 Todo 对象造出来）。
    正解是用数据库自己算：JOIN + func.count + group_by。

    提示：
      - select(User.name, func.count(Todo.id)).join(Todo).group_by(User.name)
      - session.execute(stmt).all() 拿到的是 Row，可以 row.name / row[1]
        （或者自己给 count 起个 label）

    例如: → {"小明": 3, "小红": 3, "小刚": 3}
    """
    # TODO
    stmt = select(User.name, func.count(Todo.id)).join(Todo).group_by(User.name)
    rows = session.execute(stmt).all()
    return {name: cnt for name, cnt in rows}


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []
    seed()

    # 用户数（练习 2 期望的 N）
    with Session(engine) as _s:
        N = len(_s.scalars(select(User)).all())

    # ---- 练习 1 ----
    with Session(engine) as s:
        res, n = run_counting(get_all_user_names, s)
    ok = isinstance(res, list) and sorted(res) == sorted(EXPECTED_TITLES)
    if not ok:
        errors.append(f"练习1 结果错：期望 {sorted(EXPECTED_TITLES)}，实际 {res}")
    if n != 1:
        errors.append(f"练习1 SQL 条数错：期望 1 条，实际 {n} 条")

    # ---- 练习 2 ----
    with Session(engine) as s:
        res, n = run_counting(get_users_with_todos_naive, s)
    ok = isinstance(res, dict) and {k: list(v) for k, v in res.items()} == EXPECTED_TITLES
    if not ok:
        errors.append(f"练习2 结果错：期望 {EXPECTED_TITLES}，实际 {res}")
    if n != 1 + N:
        errors.append(f"练习2 SQL 条数错：期望 {1 + N} 条（1+{N} 就是 N+1），实际 {n} 条")

    # ---- 练习 3 ----
    with Session(engine) as s:
        res, n = run_counting(get_users_with_todos_selectin, s)
    ok = isinstance(res, dict) and {k: list(v) for k, v in res.items()} == EXPECTED_TITLES
    if not ok:
        errors.append(f"练习3 结果错：期望 {EXPECTED_TITLES}，实际 {res}")
    if n != 2:
        errors.append(f"练习3 SQL 条数错：期望 2 条，实际 {n} 条（检查 selectinload 写对没）")

    # ---- 练习 4 ----
    with Session(engine) as s:
        res, n = run_counting(get_users_with_todos_joined, s)
    ok = isinstance(res, dict) and {k: list(v) for k, v in res.items()} == EXPECTED_TITLES
    if not ok:
        errors.append(f"练习4 结果错：期望 {EXPECTED_TITLES}，实际 {res}")
    if n != 1:
        errors.append(f"练习4 SQL 条数错：期望 1 条，实际 {n} 条（检查 joinedload + .unique()）")

    # ---- 练习 5 ----
    with Session(engine) as s:
        res, n = run_counting(get_todos_with_user_joined, s)
    expected5 = sorted(
        [(t, name) for name, titles in EXPECTED_TITLES.items() for t in titles]
    )
    ok = isinstance(res, list) and sorted([tuple(x) for x in res]) == expected5
    if not ok:
        errors.append(f"练习5 结果错：期望 {len(expected5)} 个 (标题, 用户名) 元组，实际 {res}")
    if n != 1:
        errors.append(f"练习5 SQL 条数错：期望 1 条，实际 {n} 条")

    # ---- 练习 6 ----
    with Session(engine) as s:
        res, n = run_counting(count_todos_per_user, s)
    expected6 = {"小明": 3, "小红": 3, "小刚": 3}
    ok = isinstance(res, dict) and dict(res) == expected6
    if not ok:
        errors.append(f"练习6 结果错：期望 {expected6}，实际 {res}")
    if n != 1:
        errors.append(f"练习6 SQL 条数错：期望 1 条，实际 {n} 条（别遍历 u.todos，让数据库去数）")

    # ---- 汇总 ----
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！10 N+1 Problem = ✅")
