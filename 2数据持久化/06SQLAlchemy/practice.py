"""
第二阶段 · 学习项 6 SQLAlchemy 2.0 — ORM 练习

学习项 5 你用原生 SQL（psycopg）操作数据库。
学习项 6 换成 ORM：用「Python 对象」操作数据库，不写 SQL 字符串。

每个函数的 TODO 需要你来实现。
写完后运行: python practice.py
全部通过 = 学习项 6 过关 ✅
"""

# ============================================
# 第一部分：连接配置（已写好，直接使用，别改）
# ============================================
from sqlalchemy import create_engine, select, update, delete, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, sessionmaker, relationship
from sqlalchemy.schema import ForeignKey

# 数据库连接串：本地 PostgreSQL 的 todo_orm_db（练习库）
DBURL = "postgresql+psycopg:///todo_orm_db"

engine = create_engine(DBURL)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。你在练习里定义的类都要继承它。"""
    pass


def reset_db():
    """清空并重建所有表，让每次运行从干净状态开始。"""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    return SessionLocal()


# ============================================
# 练习 1：定义 ORM 模型（把「表」写成「类」）
# ============================================
"""
你需要定义两个模型类（继承上面的 Base）：

User（对应表 users）
  - id    : 整型，主键          ——  Mapped[int] + primary_key=True
  - name  : 字符串              ——  Mapped[str]
  - email : 字符串              ——  Mapped[str]

Todo（对应表 todos）—— 这一轮先只定义基础列，关系（外键）留给「练习 6」
  - id    : 整型，主键
  - title : 字符串
  - done  : 布尔               ——  Mapped[bool]

提示（2.0 写法）：
  - 类名用单数（User），表名用复数（__tablename__ = "users"）
  - 用 Mapped[类型] + mapped_column()，别用旧版 Column()
  - Mapped[int] 的语法 == 你 0.3 学的 def foo(x: int)
"""

# 在这里写你的 User 类和 Todo 类：
# TODO

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    email: Mapped[str] = mapped_column()
    todos: Mapped[list['Todo']] = relationship(back_populates="user")

class Todo(Base):
    __tablename__ = 'todos'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    done: Mapped[bool] = mapped_column(default=False)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    user: Mapped['User'] = relationship(back_populates='todos')
    


# ============================================
# 练习 2：Session 新增（INSERT）
# ============================================
def create_user(session: Session, name: str, email: str) -> "User":
    """
    创建一个 User 对象并写进数据库，返回这个 User 对象。

    提示：
      - user = User(name=..., email=...) 造对象
      - session.add(user) 挂进会话
      - session.commit() 提交（真正写库）
    返回：user
    """
    # TODO
    user = User(name=name, email=email)
    session.add(user)
    session.commit()
    return user


def count_users(session: Session) -> int:
    """
    统计 users 表里一共有多少行，返回数量。

    提示：
      - 用 select(func.count()) 或 查出来再 len()
      - 关键词：func.count()

    例如：库里有 3 个用户 → 返回 3
    """
    # TODO
    stmt = select(func.count()).select_from(User)
    res = session.execute(stmt)
    return res.scalar()


# ============================================
# 练习 3：Session 查询（按 id 取一行 / 按字段找）
# ============================================
def get_user(session: Session, user_id: int) -> "User | None":
    """
    按主键 id 查一个用户，找到返回该 User 对象，找不到返回 None。

    提示：session.get(User, user_id) 是查主键的专用方法
    """
    # TODO
    return session.get(User, user_id)


def find_user_by_email(session: Session, email: str) -> "User | None":
    """
    按 email 找一个用户，返回 User 或 None。

    提示：select(User).where(User.email == email)
    """
    # TODO
    stmt = select(User).where(User.email == email)
    res = session.execute(stmt)
    return res.scalars().first()


# ============================================
# 练习 4：Session 修改（UPDATE）
# ============================================
def update_email(session: Session, user_id: int, new_email: str) -> bool:
    """
    把指定 id 用户的 email 改成 new_email，成功返回 True。

    提示：
      - 先查到对象，改 user.email = new_email，再 commit
      - 或者用 update(User).where(...).values(email=...)
    若该 id 不存在，返回 False
    """
    # TODO
    user = session.get(User, user_id)
    if user:
        user.email = new_email
        session.commit()
        return True
    else:
        return False


# ============================================
# 练习 5：Session 删除（DELETE）
# ============================================
def delete_user(session: Session, user_id: int) -> bool:
    """
    删除指定 id 的用户，成功返回 True，id 不存在返回 False。

    提示：session.delete(对象) 再 commit
    """
    # TODO
    user = session.get(User, user_id)
    if user:
        session.delete(user)
        session.commit()
        return True
    else:
        return False


# ============================================
# 练习 6：select 高级查询（排序 / 分页 / 条件组合）
# ============================================
def list_users_by_name(session: Session, keyword: str) -> list["User"]:
    """
    查出 name 里有 keyword 的用户，按 name 升序，返回 User 列表。

    提示：
      - User.name.contains(keyword) 或 User.name.like(f"%{keyword}%")
      - .order_by(User.name)
      - 用 session.execute(...).scalars().all()
    """
    # TODO
    stmt = select(User).where(User.name.contains(keyword)).order_by(User.name)
    res = session.execute(stmt)
    return res.scalars().all()


def top_users(session: Session, limit: int) -> list["User"]:
    """
    取前 limit 个用户（按 email 降序），返回 User 列表。

    提示：.order_by(User.email.desc()).limit(limit)
    """
    # TODO
    stmt = select(User).order_by(User.email.desc()).limit(limit)
    res = session.execute(stmt)
    return res.scalars().all()


# ============================================
# 练习 7：一对多关系（外键 + relationship）
# ============================================
"""
上一轮 Todo 只有基础列。现在给两表建立「一对多」关系：
一个 User 有多个 Todo（1 个用户 → 多个待办）。

需要两步：
  1) 在 Todo 类里加一列 user_id 外键：
       user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
     并加一个指向所属用户的反向引用：
       user: Mapped["User"] = relationship(back_populates="todos")

  2) 在 User 类里加一行，声明「这个用户有哪些 todo」：
       todos: Mapped[list["Todo"]] = relationship(back_populates="user")

注意：FK("users.id") 写的是「表名.列名」，外键必须指向主键。
写好后，删掉 reset_db() 第一行的 drop_all 注释？不用——reset_db 会自动重建新表结构。
"""

def add_user_todo(session: Session, user_id: int, title: str) -> "Todo":
    """
    给指定 user_id 的用户新增一个 todo，返回这个 Todo 对象。

    提示：
      - 先 get_user 查到 User，再用 relationship 挂：user.todos.append(...)
      - 或 Todo(user_id=user_id, title=title)
      - 记得 commit
    """
    # TODO
    user = session.get(User, user_id)
    todo = Todo(title=title)
    user.todos.append(todo)
    session.commit()
    return todo

def get_user_todos(session: Session, user_id: int) -> list["Todo"]:
    """
    查指定用户的所有 todo，返回 list[Todo]。

    提示：session.get(User, user_id).todos  即可（关系是反过来的）
         或 select(Todo).where(Todo.user_id == user_id)
    """
    # TODO
    user = session.get(User, user_id)
    return user.todos


# ============================================
# 测试代码，不要修改下面内容
# ============================================
def _model_ok():
    """检查练习 1 的模型定义是否到位。"""
    errors = []
    try:
        User = globals().get("User")
        Todo = globals().get("Todo")
        if User is None:
            errors.append("没有看到 User 类，你定义了吗？")
        else:
            cols = User.__table__.columns
            if not set(cols.keys()).issuperset({"id", "name", "email"}):
                errors.append(f"User 类应有 id/name/email 列，实际是 {list(cols.keys())}")
            if not cols["id"].primary_key:
                errors.append("User.id 应该是主键（primary_key=True）")
        if Todo is None:
            errors.append("没有看到 Todo 类，你定义了吗？")
        else:
            cols = Todo.__table__.columns
            if not set(cols.keys()).issuperset({"id", "title", "done"}):
                errors.append(f"Todo 类应有 id/title/done 列，实际是 {list(cols.keys())}")
    except Exception as e:
        errors.append(f"模型定义检查异常: {e}")
    return errors


if __name__ == "__main__":
    errors = []

    # 练习 1：模型定义
    errors += _model_ok()

    if set(globals()).issuperset({"User", "Todo"}):
        session = reset_db()

        # 练习 2：新增
        u = create_user(session, "zhibo", "z@test.com")
        u2 = create_user(session, "alice", "a@test.com")
        if not (u and u.id and u2 and u2.id):
            errors.append("练习2：create_user 应该返回带 id 的 User 对象")
        cu = count_users(session)
        if cu != 2:
            errors.append(f"练习2：count_users 应返回 2，实际 {cu}")

        # 练习 3：查询
        g = get_user(session, u.id)
        if g is None or g.name != "zhibo":
            errors.append("练习3：get_user 按 id 查不到刚创建的用户")
        if get_user(session, 999999) is not None:
            errors.append("练习3：get_user 对不存在的 id 应返回 None")
        fe = find_user_by_email(session, "a@test.com")
        if fe is None or fe.name != "alice":
            errors.append("练习3：find_user_by_email 找不到 alice")
        if find_user_by_email(session, "不存在@x.com") is not None:
            errors.append("练习3：find_user_by_email 不存在的应返回 None")

        # 练习 4：修改
        ok = update_email(session, u.id, "new@test.com")
        if not ok:
            errors.append("练习4：update_email 应返回 True")
        if find_user_by_email(session, "new@test.com") is None:
            errors.append("练习4：email 没改成功")
        if update_email(session, 999999, "x@x.com") is not False:
            errors.append("练习4：不存在的 id 应返回 False")

        # 练习 5：删除
        okdel = delete_user(session, u2.id)
        if not okdel:
            errors.append("练习5：delete_user 应返回 True")
        if get_user(session, u2.id) is not None:
            errors.append("练习5：用户还在？删除失败")
        if delete_user(session, 999999) is not False:
            errors.append("练习5：不存在的 id 应返回 False")

        # 练习 6：select 高级查询
        create_user(session, "bob", "b@test.com")
        create_user(session, "zhibo2", "z2@test.com")
        keyword_list = list_users_by_name(session, "zhibo")
        if not keyword_list or len(keyword_list) != 2:
            errors.append(f"练习6：list_users_by_name('zhibo') 应返回 2 个，实际 {len(keyword_list)}")
        names = [x.name for x in keyword_list]
        if names != sorted(names):
            errors.append("练习6：结果应按 name 升序")
        tops = top_users(session, 2)
        if len(tops) != 2:
            errors.append("练习6：top_users(2) 应返回 2 个")
        if tops[0].name != "zhibo2":
            errors.append(f"练习6：按 email 降序，第一个应是 zhibo2，实际 {tops[0].name if tops else '空'}")

        # 练习 7：关系
        main = find_user_by_email(session, "new@test.com")
        t1 = add_user_todo(session, main.id, "写笔记")
        t2 = add_user_todo(session, main.id, "做题")
        if not (t1 and t1.id and t2 and t2.id):
            errors.append("练习7：add_user_todo 应返回带 id 的 Todo")
        todos = get_user_todos(session, main.id)
        if len(todos) != 2:
            errors.append(f"练习7：该用户应有 2 个 todo，实际 {len(todos)}")
        if not hasattr(main, "todos") or len(main.todos) != 2:
            errors.append("练习7：User.todos 关系没生效，应能直接访问 main.todos")

    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  ❌ " + str(e))
    else:
        print("🎉 全部通过！学习项 6 SQLAlchemy 2.0 = ✅")
