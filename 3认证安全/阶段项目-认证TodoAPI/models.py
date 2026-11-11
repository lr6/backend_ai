"""
第三阶段 · 阶段项目 · Task 1 — models.py
ORM 模型：User 与 Todo

和第二阶段相比，唯一的区别是：
    users 表多了一列 password_hash —— 存的是 bcrypt 哈希串，不是明文密码。

todo 部分原样搬过来，你要做的是补上 User 的密码列。

写完后运行: ../../.venv/bin/python models.py
全部通过 = Task 1A 过关 ✅
"""

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


# ===== User 模型 =====
class User(Base):
    """
    用户表。

    已有字段：
      id        Mapped[int]        主键
      username  Mapped[str]        String(50)，unique=True
      email     Mapped[str | None] String(100)，可空

    TODO 1：加一列 password_hash
      - 名字必须是 password_hash（不是 password —— 说明这里存的是什么）
      - 类型 Mapped[str]，String(255)
      - 不允许为空
      - 和 id 一样用 mapped_column(...) 声明
    """
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str | None] = mapped_column(String(100))

    password_hash: Mapped[str] = mapped_column(String(255))
    todos: Mapped[list["Todo"]] = relationship(back_populates="user")


# ===== Todo 模型（照搬，不用改）=====
class Todo(Base):
    """
    待办表。

      id       Mapped[int]  主键
      title    Mapped[str]  String(200)
      done     Mapped[bool] default=False
      user_id  Mapped[int]  外键 → users.id
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

    for name in ("users", "todos"):
        if name not in tables:
            errors.append(f"metadata 里没有表 {name}")
        else:
            print(f"✅ 表 {name} 已注册")

    users = tables.get("users")
    todos = tables.get("todos")

    if users is not None:
        want = {"id", "username", "email", "password_hash"}
        got = set(users.columns.keys())
        if not want <= got:
            errors.append(f"users 缺列: {sorted(want - got)}（实际: {sorted(got)}）")
        else:
            print(f"✅ users 列: {sorted(got)}")

        if "password" in users.columns:
            errors.append("users 不应该有 password 列 —— 明文密码绝不能入库")
        else:
            print("✅ 没有明文 password 列")

        if "password_hash" in users.columns:
            col = users.columns["password_hash"]
            if col.nullable:
                errors.append("password_hash 应该 NOT NULL（Mapped[str] 自动非空）")
            elif not isinstance(col.type, String):
                errors.append(f"password_hash 类型应为 String(255)，实际 {col.type!r}")
            elif col.type.length != 255:
                errors.append(f"password_hash 长度应为 255，实际 {col.type.length!r}")
            else:
                print("✅ password_hash 非空 + String(255)")

    if todos is not None:
        want = {"id", "title", "done", "user_id"}
        got = set(todos.columns.keys())
        if not want <= got:
            errors.append(f"todos 缺列: {sorted(want - got)}")
        else:
            print(f"✅ todos 列: {sorted(got)}")

    # relationship 两端镜像
    try:
        user_rels = set(User.__mapper__.relationships.keys())
        todo_rels = set(Todo.__mapper__.relationships.keys())
        if not {"todos"} <= user_rels or not {"user"} <= todo_rels:
            errors.append(f"relationship 不完整: User={user_rels}, Todo={todo_rels}")
        elif User.__mapper__.relationships["todos"].back_populates != "user" or \
                Todo.__mapper__.relationships["user"].back_populates != "todos":
            errors.append("back_populates 两端指向不对")
        else:
            print("✅ relationship 两端镜像正确")
    except Exception as e:
        errors.append(f"检查 relationship 出错: {type(e).__name__}: {e}")

    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 Task 1A 通过！models.py = ✅")
