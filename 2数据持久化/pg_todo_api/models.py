"""
第二阶段 · 阶段项目 · Task 2 — models.py
ORM 模型：User 与 Todo

要定义的东西：
  User  —— users 表：id / username / email
  Todo  —— todos 表：id / title / done / user_id

外加一段双向关系：User.todos ↔ Todo.user

注意：models.py 要 import database（拿 Base），
      database.py 反过来【不要】import models —— 避免循环引用。

写完后运行: .venv/bin/python models.py
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# ===== User 模型 =====
class User(Base):
    """
    用户表。

    __tablename__ 必须写（学习项 7 就因为漏了它报 InvalidRequestError）。

    字段：
      id        Mapped[int]        主键
      username  Mapped[str]        String(50)，unique=True
      email     Mapped[str | None] String(100)，可空
    """
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str | None] = mapped_column(String(100))
    todos: Mapped[list["Todo"]] = relationship(back_populates="user")


# ===== Todo 模型 =====
class Todo(Base):
    """
    待办表。

    字段：
      id       Mapped[int]  主键
      title    Mapped[str]  String(200)
      done     Mapped[bool] default=False（用 mapped_column 的 default 参数）
      user_id  Mapped[int]  外键 → users.id，用 ForeignKey("users.id")
    """
    __tablename__ = 'todos'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(default=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped["User"] = relationship(back_populates="todos")



# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []
    tables = Base.metadata.tables

    # 测试 1：两张表都注册进 metadata（__tablename__ 写对了吗）
    for name in ("users", "todos"):
        if name not in tables:
            errors.append(f"metadata 里没有表 {name} —— 检查类是否继承 Base、__tablename__ 是否写对")
        else:
            print(f"✅ 表 {name} 已注册")

    users = tables.get("users")
    todos = tables.get("todos")

    # 测试 2：users 的列和唯一约束
    if users is not None:
        want = {"id", "username", "email"}
        got = set(users.columns.keys())
        if not want <= got:
            errors.append(f"users 缺列: {sorted(want - got)}")
        else:
            print(f"✅ users 列: {sorted(got)}")
        if "username" in users.columns:
            if not users.columns["username"].unique:
                errors.append("users.username 应该是 unique=True")
            else:
                print("✅ username 唯一约束")
        if "email" in users.columns and not users.columns["email"].nullable:
            errors.append("users.email 应该可空（Mapped[str | None]）")

    # 测试 3：todos 的列、默认值、外键
    if todos is not None:
        want = {"id", "title", "done", "user_id"}
        got = set(todos.columns.keys())
        if not want <= got:
            errors.append(f"todos 缺列: {sorted(want - got)}")
        else:
            print(f"✅ todos 列: {sorted(got)}")

        if "done" in todos.columns:
            col = todos.columns["done"]
            if col.nullable:
                errors.append("todos.done 应该是 NOT NULL（Mapped[bool] 自动非空）")
            elif col.default is None or col.default.arg is not False:
                errors.append("todos.done 应该有 default=False")
            else:
                print("✅ done 非空 + default=False")

        if "user_id" in todos.columns:
            fks = todos.columns["user_id"].foreign_keys
            targets = {fk.target_fullname for fk in fks}
            if "users.id" not in targets:
                errors.append(f"todos.user_id 外键应指向 users.id，实际: {targets or '没有外键'}")
            else:
                print("✅ user_id → users.id 外键")

    # 测试 4：relationship 两端都在（镜像）
    try:
        user_rels = set(User.__mapper__.relationships.keys())
        todo_rels = set(Todo.__mapper__.relationships.keys())
        if "todos" not in user_rels:
            errors.append(f"User 缺 relationship 'todos'（实际: {user_rels or '无'}）")
        else:
            print("✅ User.todos")
        if "user" not in todo_rels:
            errors.append(f"Todo 缺 relationship 'user'（实际: {todo_rels or '无'}）")
        else:
            print("✅ Todo.user")

        # 两端是否用 back_populates 连上了（同一个 relationship 的两头）
        if "todos" in user_rels and "user" in todo_rels:
            a = User.__mapper__.relationships["todos"].back_populates
            b = Todo.__mapper__.relationships["user"].back_populates
            if a is None or b is None:
                errors.append("relationship 两端应该用 back_populates 互相指（镜像）")
            elif a != "user" or b != "todos":
                errors.append(f"back_populates 指向不对: User.todos→{a!r}, Todo.user→{b!r}")
            else:
                print("✅ back_populates 两端镜像正确")
    except Exception as e:
        errors.append(f"检查 relationship 时出错: {type(e).__name__}: {e}")

    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 Task 2 通过！models.py = ✅")
