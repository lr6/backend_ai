"""
第二阶段 · 学习项 8 Transactions — 事务与隔离级别 检验练习

前置条件（已经帮你配好）：
  1. PostgreSQL 服务已启动
  2. 练习库 transaction_practice_db 已创建
  3. psycopg / SQLAlchemy 已安装到 .venv

你需要：在每个函数的 TODO 处补全代码。
写完后运行: .venv/bin/python practice.py
全部通过 = 学习项 8 过关 ✅

============================================
 关键背景（先看懂再动手）
============================================
 事务（Transaction）= 一组 SQL 的「打包执行」：
   - COMMIT   → 全部生效（落地）
   - ROLLBACK → 全部作废（丢弃）
 就像 Git：commit 才真正落地，放弃修改就像 checkout。

 本次练习场景：银行账户转账
   表 accounts：id, name, balance
   种子数据：alice 有 100 元，bob 有 50 元

 psycopg 要点（工具用法，不是答案）：
   - 默认 autocommit=False：执行即自动开始一个事务，直到你 commit/rollback
   - conn.execute(sql, (参数,)) 执行 SQL，%s 是占位符
   - cur.fetchone() 取一行；cur.rowcount 上一条语句影响的行数
"""

import threading
import time

import psycopg
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DBURL = "postgresql+psycopg:///transaction_practice_db"
RAWURL = "dbname=transaction_practice_db"


# ============================================
# 已提供的部分：连接工具 + ORM 模型（不要改）
# ============================================
def reset_db():
    """重建 accounts 表并灌入种子数据，返回一个全新连接（事务由你控制）。"""
    with psycopg.connect(RAWURL, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS accounts")
        conn.execute("""
            CREATE TABLE accounts (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                balance INT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO accounts (name, balance) VALUES ('alice', 100), ('bob', 50)"
        )
    return new_conn()


def new_conn():
    """开一个全新的连接（autocommit=False，事务由你手动控制）。"""
    return psycopg.connect(RAWURL)


# SQLAlchemy 部分（练习 7 用）：Account 模型直接映射同一张 accounts 表
class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    balance: Mapped[int]


engine = create_engine(DBURL)
SessionLocal = sessionmaker(bind=engine)


# ============================================
# 练习 1：事务提交 COMMIT —— 原子性（成功路径）
# ============================================
def transfer(conn, from_id, to_id, amount):
    """
    在同一个事务里完成一笔转账：
      1) from 账户余额 减 amount
      2) to 账户余额 加 amount
      3) COMMIT 提交
    返回 (from 最新余额, to 最新余额)

    例如: transfer(conn, 1, 2, 30) → (70, 80)   # alice 减 30，bob 加 30

    前置：conn 是全新连接（还没执行过任何语句）。
    提示：
      - UPDATE accounts SET balance = balance - %s WHERE id = %s
      - 提交后再 SELECT 一次，把两个余额查回来
    """
    # TODO
    conn.execute('UPDATE accounts SET balance = balance - %s WHERE id = %s', (amount, from_id))
    conn.execute('UPDATE accounts SET balance = balance + %s WHERE id = %s', (amount, to_id))
    conn.commit()
    cur = conn.execute('SELECT balance FROM accounts WHERE id = %s', (from_id,))
    cur2 = conn.execute('SELECT balance FROM accounts WHERE id = %s', (to_id,))
    return (cur.fetchone()[0], cur2.fetchone()[0])


# ============================================
# 练习 2：事务回滚 ROLLBACK —— 原子性（失败路径）
# ============================================
def transfer_with_check(conn, from_id, to_id, amount):
    """
    和练习 1 一样转账，但先做余额检查：
      先 SELECT from 账户余额，如果 < amount，抛 ValueError("余额不足")，
      并 ROLLBACK（保证 from 账户的钱一分不少）。
    余额足够 → 正常转账并 COMMIT。
    返回 (from 最新余额, to 最新余额)

    例如: transfer_with_check(conn, 1, 2, 30) → (70, 80)
    例如: transfer_with_check(conn, 1, 2, 999) → 抛 ValueError

    提示：用 try / except，出错时 conn.rollback()
    """
    # TODO
    from_cur = conn.execute('SELECT balance FROM accounts WHERE id = %s', (from_id,))
    from_balance = from_cur.fetchone()[0]
    if from_balance < amount:
        raise ValueError('余额不足')
    else:
        conn.execute('UPDATE accounts SET balance = balance - %s WHERE id = %s', (amount, from_id))
        conn.execute('UPDATE accounts SET balance = balance + %s WHERE id = %s', (amount, to_id))
        conn.commit()
        cur = conn.execute('SELECT balance FROM accounts WHERE id = %s', (from_id,))
        cur_balance = cur.fetchone()[0]
        cur2 = conn.execute('SELECT balance FROM accounts WHERE id = %s', (to_id,))
        cur2_balance = cur2.fetchone()[0]
        return (cur_balance, cur2_balance)


# ============================================
# 练习 3：隔离性 —— 读不到别人「未提交」的修改（无脏读）
# ============================================
def dirty_read_check(conn_a, conn_b):
    """
    演示 PostgreSQL 里不会发生「脏读」（dirty read）：
      1) 在 conn_a 上把 alice 余额改成 0（注意：先不要 COMMIT）
      2) 在 conn_b 上读 alice 余额
      3) 最后把 conn_a ROLLBACK（撤销改动，别污染数据）
    返回 conn_b 读到的余额（int）

    预期返回 100 —— conn_b 读到的是已提交的旧值，而不是 conn_a 未提交的 0。
    """
    # TODO
    conn_a.execute("UPDATE accounts SET balance = 0 WHERE name = 'alice'")
    cur = conn_b.execute("SELECT balance FROM accounts WHERE name = 'alice'")
    conn_a.rollback()
    return cur.fetchone()[0]


# ============================================
# 练习 4：不可重复读（non-repeatable read）—— 隔离级别对比
# ============================================
def read_twice(conn_a, conn_b, isolation):
    """
    在 conn_a 的一个事务里读同一行两次，两次之间 conn_b 修改并提交这一行。
    返回 (第一次读到的值, 第二次读到的值)

    isolation 取值（字符串）：'READ COMMITTED' / 'REPEATABLE READ' / 'SERIALIZABLE'

    预期结果：
      'READ COMMITTED'   → (100, 50)    同一事务两次读不同 = 不可重复读
      'REPEATABLE READ'  → (100, 100)   快照固定，两次一致

    步骤：
      1) conn_a 开事务并指定隔离级别:
           conn_a.execute("BEGIN ISOLATION LEVEL " + isolation)
      2) conn_a 读 alice 余额 → 第一次
      3) conn_b 把 alice 余额改成 50，并 COMMIT
      4) conn_a 再读 alice 余额 → 第二次
      5) conn_a ROLLBACK（结束事务）
    """
    # TODO
    conn_a.execute('BEGIN ISOLATION LEVEL ' + isolation)
    cur_1 = conn_a.execute("SELECT balance FROM accounts WHERE name = 'alice'")
    cur_1_val = cur_1.fetchone()[0]
    conn_b.execute("UPDATE accounts SET balance = 50 WHERE name = 'alice'")
    conn_b.commit()
    cur_2 = conn_a.execute("SELECT balance FROM accounts WHERE name = 'alice'")
    cur_2_val = cur_2.fetchone()[0]
    conn_a.rollback()
    return (cur_1_val, cur_2_val)



# ============================================
# 练习 5：幻读（phantom read）—— 隔离级别对比
# ============================================
def count_twice(conn_a, conn_b, isolation):
    """
    在 conn_a 的一个事务里 SELECT COUNT(*) 两次，两次之间 conn_b 插入并提交一行。
    返回 (第一次的行数, 第二次的行数)

    isolation 取值（字符串）：'READ COMMITTED' / 'REPEATABLE READ' / 'SERIALIZABLE'

    预期结果：
      'READ COMMITTED'   → (2, 3)    同一事务两次查到不同行数 = 幻读
      'REPEATABLE READ'  → (2, 2)    快照固定，看不到新插入的行

    步骤：
      1) conn_a 开事务并指定隔离级别（同上题）
      2) conn_a 数 accounts 总行数 → 第一次
      3) conn_b 插入一个新账户 (name='carol', balance=30)，并 COMMIT
      4) conn_a 再数一次 → 第二次
      5) conn_a ROLLBACK
    """
    # TODO
    conn_a.execute('BEGIN ISOLATION LEVEL ' + isolation)
    cur1 = conn_a.execute("SELECT COUNT(*) FROM accounts")
    conn_b.execute("INSERT INTO accounts (name, balance) VALUES ('bobo', 2000)")
    conn_b.commit()
    cur2 = conn_a.execute("SELECT COUNT(*) FROM accounts")
    conn_a.rollback()
    return (cur1.fetchone()[0], cur2.fetchone()[0])




# ============================================
# 练习 6：行锁 SELECT ... FOR UPDATE
# ============================================
def lock_balance(conn, account_id):
    """
    用 SELECT ... FOR UPDATE 锁住指定账户这一行，返回它的余额。

    例如: lock_balance(conn, 2) → 50

    关键：函数只锁不提交，调用方（测试）会验证——另一个连接想 UPDATE
    这一行时会被阻塞，直到本连接 COMMIT / ROLLBACK 释放锁。
    提示：SELECT balance FROM accounts WHERE id = %s FOR UPDATE
    """
    # TODO
    cur = conn.execute("SELECT balance FROM accounts WHERE id = %s FOR UPDATE", (account_id,))
    return cur.fetchone()[0]


# ============================================
# 练习 7：SQLAlchemy Session 就是事务 —— commit / rollback
# ============================================
def sa_transfer(session, from_id, to_id, amount):
    """
    用 SQLAlchemy 的 Session 完成转账（Session 底层就是一个事务）：
      1) 用 session.get(Account, id) 查出两个账户对象
      2) 直接改对象的 balance 属性（例：a.balance = a.balance - amount）
      3) session.commit() 提交
    返回 (from 最新余额, to 最新余额)

    如果 from 余额不足：抛 ValueError("余额不足")，并且 session.rollback()。

    例如: sa_transfer(session, 1, 2, 30) → (70, 80)
    提示：对象改完属性后，commit 会自动把改动写成 UPDATE。
    """
    # TODO
    from_user = session.get(Account, from_id)
    if from_user.balance < amount: 
        raise ValueError("余额不足")
    else:
        from_user.balance = from_user.balance - amount
        to_user = session.get(Account,to_id)
        to_user.balance = to_user.balance + amount
        session.commit()
        return (from_user.balance, to_user.balance)


# ============================================
# 测试代码，不要修改下面内容
# ============================================
def _balance(conn, account_id):
    row = conn.execute(
        "SELECT balance FROM accounts WHERE id = %s", (account_id,)
    ).fetchone()
    return row[0]


if __name__ == "__main__":
    errors = []

    # ---- 练习 1：转账（提交） ----
    conn = reset_db()
    try:
        res = transfer(conn, 1, 2, 30)
        if res != (70, 80):
            errors.append(f"练习1：transfer(1,2,30) 应返回 (70,80)，实际 {res}")
        if _balance(conn, 1) != 70 or _balance(conn, 2) != 80:
            errors.append("练习1：转账后余额不对，检查 UPDATE 或 COMMIT")
    except Exception as e:
        errors.append(f"练习1：抛异常 {e!r}")
    finally:
        conn.close()

    # ---- 练习 2：转账（回滚） ----
    conn = reset_db()
    try:
        res = transfer_with_check(conn, 1, 2, 30)
        if res != (70, 80):
            errors.append(f"练习2：余额充足时应返回 (70,80)，实际 {res}")
        try:
            transfer_with_check(conn, 1, 2, 9999)
            errors.append("练习2：余额不足时应抛 ValueError")
        except ValueError:
            pass
        if _balance(conn, 1) != 70:
            errors.append("练习2：余额不足转账后，from 账户应保持 70（没被扣），"
                          f"实际 {_balance(conn, 1)}")
    except Exception as e:
        errors.append(f"练习2：抛异常 {e!r}")
    finally:
        conn.close()

    # ---- 练习 3：无脏读 ----
    conn_a = reset_db()
    conn_b = new_conn()
    try:
        got = dirty_read_check(conn_a, conn_b)
        if got != 100:
            errors.append(f"练习3：conn_b 应读到 100（未提交的改动不可见），实际 {got}")
        if _balance(conn_a, 1) != 100:
            errors.append("练习3：conn_a 撤销后 alice 应恢复 100")
    except Exception as e:
        errors.append(f"练习3：抛异常 {e!r}")
    finally:
        conn_a.close()
        conn_b.close()

    # ---- 练习 4：不可重复读 ----
    for iso, expect in [("READ COMMITTED", (100, 50)),
                        ("REPEATABLE READ", (100, 100))]:
        conn_a = reset_db()
        conn_b = new_conn()
        try:
            got = read_twice(conn_a, conn_b, iso)
            if got != expect:
                errors.append(f"练习4：{iso} 应返回 {expect}，实际 {got}")
        except Exception as e:
            errors.append(f"练习4({iso})：抛异常 {e!r}")
        finally:
            conn_a.close()
            conn_b.close()

    # ---- 练习 5：幻读 ----
    for iso, expect in [("READ COMMITTED", (2, 3)),
                        ("REPEATABLE READ", (2, 2))]:
        conn_a = reset_db()
        conn_b = new_conn()
        try:
            got = count_twice(conn_a, conn_b, iso)
            if got != expect:
                errors.append(f"练习5：{iso} 应返回 {expect}，实际 {got}")
        except Exception as e:
            errors.append(f"练习5({iso})：抛异常 {e!r}")
        finally:
            conn_a.close()
            conn_b.close()

    # ---- 练习 6：行锁 ----
    conn_a = reset_db()
    try:
        bal = lock_balance(conn_a, 2)
        if bal != 50:
            errors.append(f"练习6：lock_balance(2) 应返回 50，实际 {bal}")

        worker_done = {"v": False}

        def worker():
            cb = new_conn()
            try:
                cb.execute("UPDATE accounts SET balance = 999 WHERE id = 2")
                cb.commit()
                worker_done["v"] = True
            finally:
                cb.close()

        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.6)
        if not t.is_alive():
            errors.append("练习6：行没被锁住！worker 不应在 conn_a 提交前完成 UPDATE")
        conn_a.rollback()  # 释放锁
        t.join(timeout=3)
        if not worker_done["v"]:
            errors.append("练习6：rollback 后锁应释放，worker 应能完成 UPDATE")
    except Exception as e:
        errors.append(f"练习6：抛异常 {e!r}")
    finally:
        conn_a.close()

    # ---- 练习 7：SQLAlchemy Session 事务 ----
    conn = reset_db()
    s = SessionLocal()
    try:
        res = sa_transfer(s, 1, 2, 30)
        if res != (70, 80):
            errors.append(f"练习7：sa_transfer(1,2,30) 应返回 (70,80)，实际 {res}")
        if _balance(conn, 1) != 70:
            errors.append("练习7：Session 提交后 alice 应为 70")
        try:
            sa_transfer(s, 1, 2, 9999)
            errors.append("练习7：余额不足时应抛 ValueError")
        except ValueError:
            pass
        if _balance(conn, 1) != 70:
            errors.append("练习7：rollback 后 alice 应保持 70（没被扣），"
                          f"实际 {_balance(conn, 1)}")
    except Exception as e:
        errors.append(f"练习7：抛异常 {e!r}")
    finally:
        s.close()
        conn.close()

    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  ❌ " + str(e))
    else:
        print("🎉 全部通过！学习项 8 Transactions = ✅")
