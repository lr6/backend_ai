"""
第二阶段 · 学习项 10 N+1 Problem — 三种写法的 SQL 对比

同一个需求（3 个用户 + 各自的 todo），三种写法，数一数各发几条 SQL：
  ① 懒加载（不处理）      → 1 + N 条   ❌
  ② selectinload（预加载）→ 2 条       ✅
  ③ joinedload（预加载）  → 1 条       ✅

运行： .venv/bin/python 2数据持久化/10N+1Problem/demo_fix.py
"""

from sqlalchemy import create_engine, select, ForeignKey, event
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, Session,
    selectinload, joinedload,
)

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


# ============================================
# SQL 记录器：不开 echo，改用事件钩子把每一条 SQL 抓下来
# （event 是 SQLAlchemy 的钩子机制，每个 SQL 执行前都会回调这里）
# ============================================
caught: list[tuple[str, object]] = []


@event.listens_for(engine, "before_cursor_execute")
def _collect(conn, cursor, statement, parameters, context, executemany):
    if not statement.startswith(("BEGIN", "ROLLBACK", "COMMIT")):
        caught.append((" ".join(statement.split()), parameters))


def run(label: str, fn):
    """跑一段查询，打印它发了多少条 SQL、每条长什么样。"""
    caught.clear()
    result = fn()
    print(f"\n{'=' * 76}\n【{label}】")
    print(f"  ➜ 共 {len(caught)} 条 SQL")
    for i, (stmt, params) in enumerate(caught, 1):
        show = stmt if len(stmt) <= 150 else stmt[:147] + "..."
        print(f"     {i}. {show}")
        print(f"        参数: {params}")
    print(f"  ➜ 结果: {result}")
    return result


# ============================================
# 准备数据
# ============================================
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
with Session(engine) as s:
    for name in ["小明", "小红", "小刚"]:
        s.add(User(name=name, todos=[Todo(title=f"{name}的任务{i}") for i in range(1, 4)]))
    s.commit()

print("数据已就绪：3 个用户，每人 3 个 todo")
print("下面三种写法做的是「同一件事」：返回 [(用户名, [他的todo标题...]), ...]")

# ============================================
# ① 懒加载 —— N+1 现场
# ============================================
def naive():
    with Session(engine) as s:
        users = s.scalars(select(User)).all()
        return [(u.name, [t.title for t in u.todos]) for u in users]  # 👈 每次访问触发一条


# ============================================
# ② selectinload —— 第二条 SQL 用 IN (...)
# ============================================
def with_selectinload():
    with Session(engine) as s:
        stmt = select(User).options(selectinload(User.todos))  # 👈 关键就这一句
        users = s.scalars(stmt).all()
        return [(u.name, [t.title for t in u.todos]) for u in users]


# ============================================
# ③ joinedload —— 一条 SQL LEFT JOIN 到底
# ============================================
def with_joinedload():
    with Session(engine) as s:
        stmt = select(User).options(joinedload(User.todos))  # 👈 换成 joinedload
        users = s.scalars(stmt).unique().all()               # 👈 joinedload 记得 .unique()
        return [(u.name, [t.title for t in u.todos]) for u in users]


run("① 懒加载（不处理）—— 看 N+1", naive)
run("② selectinload —— 2 条", with_selectinload)
run("③ joinedload —— 1 条", with_joinedload)

print(f"\n{'=' * 76}")
print("对比结论：")
print("  ① 1 + N 条  —— N 越大越慢，100 个用户 = 101 条 SQL")
print("  ② 2 条      —— 固定 2 条，跟用户数无关")
print("  ③ 1 条      —— 固定 1 条，但数据会重复（JOIN 的特性）")
print("=" * 76)
