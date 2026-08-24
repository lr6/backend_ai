"""
第二阶段 · 5 PostgreSQL — 表设计（约束、主键、外键）检验练习

前置条件：PostgreSQL 已启动、todo_db 已创建、psycopg 已装。

写完运行: .venv/bin/python practice_table_design.py
全部通过 = 表设计过关 ✅

psycopg 用法速查（同上一课）:
  conn.execute(sql)              执行 SQL，返回 cursor
  conn.execute(sql, (参数,))     参数化（%s 占位符）
  cur.fetchone()                 取一行
  cur.fetchall()                 取所有行
"""

import psycopg

CONN_STRING = "dbname=todo_db"


def get_conn():
    """返回一个已连接的数据库连接（自动提交）。不用改。"""
    return psycopg.connect(CONN_STRING, autocommit=True)


# ===== 练习 1：建 users 表（含约束） =====
def create_users_table(conn):
    """
    创建 users 表，包含四列：
      - id       : 自增主键  SERIAL PRIMARY KEY
      - username : 文本，不能为空且唯一  TEXT NOT NULL UNIQUE
      - email    : 文本，不能为空且唯一  TEXT NOT NULL UNIQUE
      - age      : 整数，必须在 0~150 之间  INTEGER CHECK (age >= 0 AND age <= 150)

    执行后表 users 存在即可。
    """
    # TODO: 写 CREATE TABLE 语句并执行
    conn.execute('''
        CREATE TABLE users(
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            age INTEGER CHECK (age >= 0 AND age <= 150)
        )
    ''')


# ===== 练习 2：建 todos 表（含外键） =====
def create_todos_table(conn):
    """
    创建 todos 表，包含三列：
      - id      : 自增主键  SERIAL PRIMARY KEY
      - title   : 文本，不能为空  TEXT NOT NULL
      - user_id : 整数，不能为空，且引用 users 表的 id  INTEGER NOT NULL REFERENCES users(id)

    执行后表 todos 存在即可。
    """
    # TODO: 写 CREATE TABLE 语句并执行
    conn.execute('''
        CREATE TABLE todos(
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            user_id INTEGER NOT NULL REFERENCES users(id)
        )
    ''')


# ===== 练习 3：插入用户（INSERT） =====
def insert_user(conn, username, email, age):
    """
    向 users 表插入一条记录，返回新 id。
    例如: insert_user(conn, "alice", "alice@x.com", 25) → 1

    提示：INSERT INTO users (username, email, age) VALUES (%s, %s, %s) RETURNING id
    """
    # TODO
    cur = conn.execute('INSERT INTO users (username, email, age) VALUES (%s, %s, %s) RETURNING id', (username, email, age,))
    return cur.fetchone()[0]


# ===== 练习 4：插入 todo（INSERT + 外键） =====
def insert_todo(conn, title, user_id):
    """
    向 todos 表插入一条记录，返回新 id。
    例如: insert_todo(conn, "买牛奶", 1) → 1

    提示：INSERT INTO todos (title, user_id) VALUES (%s, %s) RETURNING id
    """
    # TODO
    cur = conn.execute('INSERT INTO todos (title, user_id) VALUES (%s, %s) RETURNING id', (title, user_id))
    return cur.fetchone()[0]


# ===== 练习 5：按用户名查用户（SELECT WHERE + UNIQUE 列） =====
def get_user_by_username(conn, username):
    """
    按 username 查用户，返回这一行（tuple）或 None（查不到时）。
    例如: get_user_by_username(conn, "alice") → (1, 'alice', 'alice@x.com', 25)

    提示：SELECT * FROM users WHERE username = %s，用 fetchone()
    """
    # TODO
    cur = conn.execute('SELECT * FROM users WHERE username = %s', (username,))
    return cur.fetchone()


# ===== 练习 6：感受 UNIQUE 约束 =====
def insert_duplicate_username(conn):
    """
    尝试插入一个 username = 'alice' 的用户（测试环境里已经有 alice 了）。
    因为 username 是 UNIQUE，这次插入会被数据库拒绝（抛异常）。

    用 try/except 捕获异常：
      - 插入失败（被约束拦截）→ 返回 False
      - 意外成功 → 返回 True

    提示：
      try:
          conn.execute("INSERT INTO users ...")
          return True
      except Exception:
          return False
    """
    # TODO
    try:
        conn.execute("INSERT INTO users (username, email, age) VALUES ('alice', 'd@qq.com', 22)")
        return True
    except Exception:
        return False


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []
    conn = get_conn()

    # 清理：先删 todos（有外键引用 users），再删 users
    conn.execute("DROP TABLE IF EXISTS todos")
    conn.execute("DROP TABLE IF EXISTS users")

    # ---- 练习 1：create_users_table ----
    try:
        create_users_table(conn)
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'users'"
        ).fetchall()
        cols = {r[0] for r in rows}
        if cols != {"id", "username", "email", "age"}:
            errors.append(f"❌ 练习1 建表：列不对，期望 {{id, username, email, age}}，实际 {cols}")
    except Exception as e:
        errors.append(f"❌ 练习1 建表报错：{e}")

    # ---- 练习 1 附加：验证 NOT NULL / CHECK 约束 ----
    try:
        # NOT NULL：插入 NULL username 应报错
        try:
            conn.execute("INSERT INTO users (username, email, age) VALUES (NULL, 'a@x.com', 10)")
            errors.append("❌ 练习1 约束：username 的 NOT NULL 没生效（NULL 竟能插入）")
        except Exception:
            pass
        # CHECK：插入 age = -5 应报错
        try:
            conn.execute("INSERT INTO users (username, email, age) VALUES ('tmp', 'tmp@x.com', -5)")
            errors.append("❌ 练习1 约束：age 的 CHECK 没生效（负数竟能插入）")
        except Exception:
            pass
        conn.execute("TRUNCATE users RESTART IDENTITY")
    except Exception as e:
        errors.append(f"❌ 练习1 约束验证报错：{e}")

    # ---- 练习 2：create_todos_table + 验证外键 ----
    try:
        create_todos_table(conn)
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'todos'"
        ).fetchall()
        cols = {r[0] for r in rows}
        if cols != {"id", "title", "user_id"}:
            errors.append(f"❌ 练习2 建表：列不对，期望 {{id, title, user_id}}，实际 {cols}")
        # 外键：插入不存在的 user_id 应报错
        try:
            conn.execute("INSERT INTO todos (title, user_id) VALUES ('孤儿todo', 999)")
            errors.append("❌ 练习2 约束：外键没生效（user_id=999 不存在竟能插入）")
        except Exception:
            pass
        conn.execute("TRUNCATE todos RESTART IDENTITY")
    except Exception as e:
        errors.append(f"❌ 练习2 建表报错：{e}")

    # ---- 练习 3：insert_user ----
    try:
        id1 = insert_user(conn, "alice", "alice@x.com", 25)
        if id1 != 1:
            errors.append(f"❌ 练习3 插入用户：期望 id=1，实际 {id1}")
    except Exception as e:
        errors.append(f"❌ 练习3 插入用户报错：{e}")

    # ---- 练习 4：insert_todo ----
    try:
        tid = insert_todo(conn, "买牛奶", 1)
        if tid != 1:
            errors.append(f"❌ 练习4 插入 todo：期望 id=1，实际 {tid}")
        row = conn.execute("SELECT title, user_id FROM todos WHERE id = 1").fetchone()
        if row != ("买牛奶", 1):
            errors.append(f"❌ 练习4 插入 todo：内容不对，期望 ('买牛奶', 1)，实际 {row}")
    except Exception as e:
        errors.append(f"❌ 练习4 插入 todo 报错：{e}")

    # ---- 练习 5：get_user_by_username ----
    try:
        u = get_user_by_username(conn, "alice")
        if u != (1, "alice", "alice@x.com", 25):
            errors.append(f"❌ 练习5 按用户名查询：期望 (1, 'alice', 'alice@x.com', 25)，实际 {u}")
        u_none = get_user_by_username(conn, "不存在的人")
        if u_none is not None:
            errors.append(f"❌ 练习5 按用户名查询：查不到应返回 None，实际 {u_none}")
    except Exception as e:
        errors.append(f"❌ 练习5 按用户名查询报错：{e}")

    # ---- 练习 6：insert_duplicate_username ----
    try:
        result = insert_duplicate_username(conn)
        if result is not False:
            errors.append(f"❌ 练习6 UNIQUE：期望返回 False（被拦截），实际 {result}")
    except Exception as e:
        errors.append(f"❌ 练习6 UNIQUE 报错：{e}")

    # 清理
    conn.execute("DROP TABLE IF EXISTS todos")
    conn.execute("DROP TABLE IF EXISTS users")
    conn.close()

    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！表设计 = ✅")
