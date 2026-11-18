"""
第四阶段 · 阶段项目 · Task 1A — database.py
数据库基础设施：engine / SessionLocal / Base / get_db

和第二阶段、第三阶段的 database.py 几乎一样，只有一个关键区别：
    DATABASE_URL 不再写死在这里，而是从 config.py 读。

依赖方向：database.py → config.py（不 import models，避免循环引用）

写完后运行: ../../.venv/bin/python database.py
全部通过 = Task 1A database 部分 ✅
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import config

# TODO 1：创建 engine
#   用 config.DATABASE_URL，echo=False
#   提示：create_engine(config.DATABASE_URL, echo=...)
engine = create_engine(config.DATABASE_URL, echo=False)

# TODO 2：SessionLocal 工厂
#   sessionmaker(bind=...)
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


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    from sqlalchemy import text

    errors = []

    def check(name, cond, detail=""):
        if cond:
            print(f"✅ {name}")
        else:
            errors.append(f"{name} {detail}")

    # ---------- 测试 1：engine 用 config 里的地址连上了 eng_todo_db ----------
    try:
        with engine.connect() as conn:
            v = conn.execute(text("SELECT 1")).scalar()
            current_db = conn.execute(text("SELECT current_database()")).scalar()
        check("engine 能连上数据库", v == 1, f"SELECT 1 返回 {v!r}")
        check("连的是 eng_todo_db", current_db == "eng_todo_db", f"实际连的是 {current_db!r}")
    except Exception as e:
        errors.append(f"engine 连接失败: {type(e).__name__}: {e}")

    # ---------- 测试 2：get_db 是生成器，产出 Session ----------
    g = None
    try:
        g = get_db()
        db = next(g)
        check("get_db 产出 Session", db.__class__.__name__ == "Session",
              f"实际 {type(db).__name__}")
    except TypeError as e:
        errors.append(f"get_db 不是生成器（函数体里没有 yield?）: {e}")
    except Exception as e:
        errors.append(f"get_db 出错: {type(e).__name__}: {e}")

    # ---------- 测试 3：请求结束后连接归还连接池 ----------
    # 这是验证「finally 里真的 close 了」最硬的办法
    if g is not None:
        try:
            pool = engine.pool
            db.execute(text("SELECT 1"))      # 真用一下，占住一条连接
            used = pool.checkedout()
            try:
                next(g)                       # 让生成器跑完 → 触发 finally
            except StopIteration:
                pass
            after = pool.checkedout()
            check("Session 用完连接已归还", after < used,
                  f"checkedout {used} → {after}，finally 里可能漏了 db.close()")
        except Exception as e:
            errors.append(f"收场测试失败: {type(e).__name__}: {e}")

    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！Task 1A database.py = ✅")
