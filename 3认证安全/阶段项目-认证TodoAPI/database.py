"""
第三阶段 · 阶段项目 · Task 1 — database.py

和第二阶段 pg_todo_api/database.py 一样，只改了数据库名：
    todo_api_db  →  auth_todo_db

三件事：
  1. engine          —— 连接池，管「怎么连数据库」
  2. SessionLocal    —— Session 工厂，按需生产 Session
  3. get_db          —— 每个请求一个 Session，用完自动关

本文件【不 import models】，避免循环引用。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# 本机 psql 直连，无密码；+psycopg 表示用 psycopg 3 驱动
DATABASE_URL = "postgresql+psycopg:///auth_todo_db"

# echo=False：不打印 SQL。想看每条 SQL 就改成 echo=True
engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类，表结构注册到 Base.metadata。"""
    pass


def get_db():
    """
    请求级 Session 依赖（生成器函数）。

    请求进来 → 开 Session
    yield    → 把 Session 交给路由函数
    请求结束 → finally 里 close（成功或异常都归还连接）
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
