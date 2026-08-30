"""
第二阶段 · 学习项 7 Alembic — 模型定义（迁移的「目标结构」）

回忆学习项 6：用 ORM 把「表」写成「类」。
今天这个文件就是 Alembic autogenerate 的「对照物」：
  Alembic 拿这里的模型 metadata  vs  数据库当前结构
  差异 = 生成的迁移内容

请把学习项 6 练习里的 User / Todo 模型「搬」过来。
要求：
  1. 继承 Base
  2. 用 2.0 写法：Mapped[类型] + mapped_column()
  3. User（users 表）：id 主键、name、email
  4. Todo（todos 表）：id 主键、title、done（默认 False）、user_id（外键 -> users.id）
  （relationship 可写可不写 —— 它不影响表结构，但可以练手）
"""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import date


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
    pass


# TODO 把你的 User 类和 Todo 类写在这里

class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    email: Mapped[str] = mapped_column()

class Todo(Base):
    __tablename__ = 'todos'
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    done: Mapped[bool] = mapped_column(default=False)
    due_date: Mapped[date | None] = mapped_column()
    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
