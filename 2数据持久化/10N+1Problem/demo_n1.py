"""
第二阶段 · 学习项 10 N+1 Problem — 现场演示脚本

作用：真实跑一遍「懒加载 + for 循环」，让你亲眼数出 N+1 到底发了几条 SQL。

运行： .venv/bin/python 2数据持久化/10N+1Problem/demo_n1.py

看不懂的代码别慌 —— 这是给你看的「现象」，不是要你写的作业。
"""

from sqlalchemy import create_engine, select, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

DBURL = "postgresql+psycopg:///n1_practice_db"
engine = create_engine(DBURL)  # 先关着 SQL 日志，等下再打开


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    # 一对多：一个 User 有多个 Todo
    todos: Mapped[list["Todo"]] = relationship(back_populates="user")


class Todo(Base):
    __tablename__ = "todos"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="todos")


# ============================================
# 1. 准备数据：3 个用户，各自 3 个 todo
# ============================================
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)

with Session(engine) as session:
    for name in ["小明", "小红", "小刚"]:
        session.add(User(name=name, todos=[
            Todo(title=f"{name}的任务{i}") for i in range(1, 4)
        ]))
    session.commit()

print("✅ 数据准备好了：3 个用户，每人 3 个 todo\n")

# ============================================
# 2. 打开 SQL 日志，跑 N+1 代码，自己数条数
# ============================================
print("=" * 72)
print("🔍 现场开始 —— 下面会打印真实 SQL，请数一数一共几条")
print("=" * 72)

engine.echo = True  # 👈 打开 SQL 日志开关

with Session(engine) as session:
    users = session.scalars(select(User)).all()      # 你觉得这里几条？
    print("\n>>> 拿到了", len(users), "个用户，名字：", [u.name for u in users])
    print(">>> 现在遍历，逐个访问 u.todos：\n")
    for u in users:
        # 👇 每次访问 .todos，就是一次「懒加载」触发
        print(f"    {u.name}: {[t.title for t in u.todos]}")

engine.echo = False

print("\n" + "=" * 72)
print(f"☝️ 数清楚了吗？SQL 总数 = 1（查用户）+ {len(users)}（每人各查一次 todos）")
print(f"   在这个例子里 N = {len(users)}，所以是 1 + {len(users)} = {1 + len(users)} 条")
print("=" * 72)
