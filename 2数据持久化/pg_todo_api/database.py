"""
第二阶段 · 阶段项目 · Task 1 — database.py
数据库连接 与 请求级会话

这个文件是整个项目的「水管总闸」，负责三件事：
  1. 造一个 engine          —— 连接池，管「怎么连数据库」
  2. 造一个 SessionLocal    —— Session 工厂，按需生产 Session
  3. 提供 get_db 依赖        —— 每个请求一个 Session，用完自动关

注意：这个文件【不 import models】。
      它是地基，models 反过来 import 它。
      （方向 import models 会造成循环引用）

写完后运行: .venv/bin/python database.py
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# 连接串格式: 方言+驱动://用户@主机/库名
# 本机 psql 直连，没有密码，用户省略（默认用当前系统用户 zhibo）
# +psycopg  = 用 psycopg 3 这个驱动（就是我们 Task 0 装的 psycopg[binary]）
DATABASE_URL = "postgresql+psycopg:///todo_api_db"


# ===== engine =====
# 造连接池。学习项 6 你写过一行一模一样的。
# 提示：create_engine(DATABASE_URL)
#
# 【调试小技巧】加 echo=True 参数 → 每次发 SQL 都会打印出来。
#   这个项目强烈建议你打开，你能亲眼看到「懒加载」「N+1」在真项目里长什么样。
#   嫌吵就关掉。自己决定。
engine = create_engine(DATABASE_URL, echo=True)

# ===== SessionLocal =====
# Session 工厂（注意：是工厂，不是 Session 本身 —— 调它才产出 Session）
# 学习项 6 你也写过。
# 提示：sessionmaker(bind=engine)
SessionLocal = sessionmaker(bind=engine)


# ===== 地基基类（已给好，不用改）=====
# 所有 ORM 模型继承它，模型的表结构会注册到 Base.metadata 上
# → Alembic 的 autogenerate 就是拿这份 metadata 去跟数据库比的
class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
    pass


# ===== get_db =====
def get_db():
    """
    请求级 Session 依赖。

    它是「生成器函数」（函数体里有 yield）：
      请求进来 → 开 Session
      yield    → 把 Session 交给路由函数用
      请求结束 → finally 里收场

    回忆一下 yield 的语义（学习项 3 的 lifespan 也是这个套路）：
      yield 前面 = 开场，yield 后面 = 收场。

    路由里这样用它：
      def get_todos(db: Session = Depends(get_db)):
          ...

    要点：finally 必须保证「不管请求成功还是抛异常，Session 都会被关掉」。
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

    # 测试 1：engine 能不能真的连上 todo_api_db
    try:
        with engine.connect() as conn:
            v = conn.execute(text("SELECT 1")).scalar()
        if v != 1:
            errors.append(f"SELECT 1 期望 1，实际 {v}")
        else:
            print("✅ engine 连上 todo_api_db")
    except Exception as e:
        errors.append(f"engine 连接失败: {type(e).__name__}: {e}")

    # 测试 2：get_db 是不是生成器、能不能产出 Session
    try:
        g = get_db()
        db = next(g)
        print(f"✅ get_db 产出 Session: {type(db).__name__}")
    except TypeError as e:
        errors.append(f"get_db 不是生成器（函数体里没有 yield?）: {e}")
        g = None
    except Exception as e:
        errors.append(f"get_db 出错: {type(e).__name__}: {e}")
        g = None

    # 测试 3：请求结束后，Session 占用的连接有没有归还连接池
    #   —— 这是验证「finally 里真的 close 了」最硬的办法
    if g is not None:
        try:
            pool = engine.pool
            db.execute(text("SELECT 1"))       # 真用一下，占住一条连接
            used = pool.checkedout()
            try:
                next(g)                        # 让生成器跑完 → 触发 finally
            except StopIteration:
                pass
            after = pool.checkedout()
            if after < used:
                print(f"✅ 收场正常：连接已归还连接池 ({used} → {after})")
            else:
                errors.append(
                    f"连接没归还（checkedout {used} → {after}）"
                    " —— get_db 的 finally 里可能漏了 db.close()"
                )
        except Exception as e:
            errors.append(f"收场测试失败: {type(e).__name__}: {e}")

    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 Task 1 通过！database.py = ✅")
