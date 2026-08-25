"""
第二阶段 · 5 PostgreSQL — JOIN（多表关联查询）检验练习

前置条件：PostgreSQL 已启动、todo_db 已创建、psycopg 已装。

本轮聚焦「查询」，表和数据由下面的测试代码自动建好、塞好，你只需实现 6 个查询函数。

写完运行: .venv/bin/python practice_join.py
全部通过 = JOIN 过关 ✅

============================================
 测试数据一览（已经帮你准备好，不用你建）
============================================
  users 表:
    id=1  alice
    id=2  bob
    id=3  carol   ← 一条 todo 都没有，用来测 LEFT JOIN

  todos 表:
    id=1  买牛奶  user_id=1  (alice)
    id=2  写代码  user_id=1  (alice)
    id=3  开会    user_id=2  (bob)
    id=4  孤儿任务 user_id=NULL  ← 没有主人，用来测 INNER/RIGHT 的区别

============================================
 psycopg 用法速查（同前几课）
============================================
  conn.execute(sql)              执行 SQL，返回 cursor
  conn.execute(sql, (参数,))     参数化（%s 占位符）
  cur.fetchone()                 取一行（tuple 或 None）
  cur.fetchall()                 取所有行（list[tuple]）

  JOIN 语法骨架:
    SELECT t.title, u.username
    FROM todos t
    INNER JOIN users u ON t.user_id = u.id
"""

import psycopg

CONN_STRING = "dbname=todo_db"


def get_conn():
    """返回一个已连接的数据库连接（自动提交）。不用改。"""
    return psycopg.connect(CONN_STRING, autocommit=True)


# ===== 练习 1：INNER JOIN 基础 =====
def join_todos_with_users(conn):
    """
    用 INNER JOIN 查出「每个 todo 的标题 + 它的主人用户名」，按 todo id 升序。
    返回 list of tuple，例如:
        [('买牛奶', 'alice'), ('写代码', 'alice'), ('开会', 'bob')]

    注意：孤儿任务（user_id=NULL）没有主人，INNER JOIN 会自动把它排除掉。

    提示：SELECT t.title, u.username FROM todos t INNER JOIN users u ON ...
    """
    # TODO
    cur = conn.execute("SELECT t.title, u.username FROM todos t INNER JOIN users u ON t.user_id = u.id ORDER BY t.id ASC    ")
    return cur.fetchall() 


# ===== 练习 2：INNER JOIN + WHERE 过滤 =====
def get_user_todos(conn, username):
    """
    查出某个用户的所有 todo 标题，按 todo id 升序。
    返回标题列表（list of str），例如:
        get_user_todos(conn, "alice") → ['买牛奶', '写代码']

    提示：在练习 1 基础上加 WHERE u.username = %s（参数化）
    """
    # TODO
    cur = conn.execute("SELECT t.title, u.username FROM todos t INNER JOIN users u ON u.id = t.user_id WHERE u.username = %s ORDER BY t.id ASC", (username,))
    return [x[0] for x in cur.fetchall()]


# ===== 练习 3：INNER JOIN 查单个 =====
def get_todo_owner(conn, todo_id):
    """
    查某一条 todo 的标题和它的主人用户名。
    返回一个 tuple (title, username)，查不到返回 None。
    例如: get_todo_owner(conn, 1) → ('买牛奶', 'alice')

    提示：SELECT t.title, u.username ... WHERE t.id = %s，用 fetchone()
    """
    # TODO
    cur = conn.execute("SELECT t.title, u.username FROM todos t INNER JOIN users u ON t.user_id = u.id WHERE t.id = %s", (todo_id,))
    return cur.fetchone()


# ===== 练习 4：LEFT JOIN 找「没有 todo 的用户」 =====
def get_users_without_todos(conn):
    """
    用 LEFT JOIN 找出「一条 todo 都没有」的用户，返回用户名列表（按 id 升序）。
    测试数据里应该是: ['carol']

    提示：
      1. FROM users u LEFT JOIN todos t ON t.user_id = u.id
      2. 右表（todos）匹配不上的行，t.id 会是 NULL
      3. 用 WHERE t.id IS NULL 筛出这些行
    """
    # TODO
    cur = conn.execute("SELECT u.username FROM users u LEFT JOIN todos t ON t.user_id = u.id WHERE t.id is NULL")
    return [cur.fetchone()[0]]


# ===== 练习 5：LEFT JOIN + GROUP BY 聚合统计 =====
def count_todos_per_user(conn):
    """
    统计每个用户有多少条 todo（没有 todo 的用户 count 也要出现，为 0）。
    按用户 id 升序，返回 list of tuple，例如:
        [('alice', 2), ('bob', 1), ('carol', 0)]

    提示：
      1. FROM users u LEFT JOIN todos t ON t.user_id = u.id
      2. SELECT u.username, COUNT(t.id)
      3. GROUP BY u.id, u.username   （按用户分组）
      4. 为什么用 COUNT(t.id) 而不是 COUNT(*)：没 todo 的用户要数出 0
    """
    # TODO
    cur = conn.execute("SELECT u.username, count(t.id) FROM users u LEFT JOIN todos t ON t.user_id = u.id GROUP BY u.username, u.id ORDER BY u.id ASC")
    return cur.fetchall()

# ===== 练习 6：RIGHT JOIN =====
def right_join_all_todos(conn):
    """
    用 RIGHT JOIN 列出「所有 todo 的标题 + 主人用户名」，按 todo id 升序。
    没有主人的 todo，username 那一列返回 None。例如:
        [('买牛奶', 'alice'), ('写代码', 'alice'), ('开会', 'bob'), ('孤儿任务', None)]

    提示：FROM users u RIGHT JOIN todos t ON t.user_id = u.id
          （保留右表 todos 的全部行，孤儿任务 user_id=NULL 也会出现）
    """
    # TODO
    cur = conn.execute("SELECT t.title, u.username FROM users u RIGHT JOIN todos t ON t.user_id = u.id ORDER BY t.id ASC")
    return cur.fetchall()


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []
    conn = get_conn()

    # ---- 搭建测试数据（建表 + 插数据）----
    conn.execute("DROP TABLE IF EXISTS todos")
    conn.execute("DROP TABLE IF EXISTS users")
    conn.execute("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            age INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE todos (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            user_id INTEGER   -- 故意允许 NULL，好让「孤儿任务」存在
        )
    """)
    conn.execute("INSERT INTO users (username, email, age) VALUES (%s, %s, %s)", ("alice", "alice@x.com", 25))
    conn.execute("INSERT INTO users (username, email, age) VALUES (%s, %s, %s)", ("bob", "bob@x.com", 30))
    conn.execute("INSERT INTO users (username, email, age) VALUES (%s, %s, %s)", ("carol", "carol@x.com", 28))
    conn.execute("INSERT INTO todos (title, user_id) VALUES (%s, %s)", ("买牛奶", 1))
    conn.execute("INSERT INTO todos (title, user_id) VALUES (%s, %s)", ("写代码", 1))
    conn.execute("INSERT INTO todos (title, user_id) VALUES (%s, %s)", ("开会", 2))
    conn.execute("INSERT INTO todos (title, user_id) VALUES (%s, NULL)", ("孤儿任务",))

    # ---- 练习 1：INNER JOIN 基础 ----
    try:
        rows = join_todos_with_users(conn)
        expected = [("买牛奶", "alice"), ("写代码", "alice"), ("开会", "bob")]
        if rows != expected:
            errors.append(f"❌ 练习1 INNER JOIN：期望 {expected}，实际 {rows}")
    except Exception as e:
        errors.append(f"❌ 练习1 INNER JOIN 报错：{e}")

    # ---- 练习 2：INNER JOIN + WHERE ----
    try:
        rows = get_user_todos(conn, "alice")
        if rows != ["买牛奶", "写代码"]:
            errors.append(f"❌ 练习2 查用户 todos：期望 ['买牛奶', '写代码']，实际 {rows}")
        rows2 = get_user_todos(conn, "bob")
        if rows2 != ["开会"]:
            errors.append(f"❌ 练习2 查用户 todos：期望 ['开会']，实际 {rows2}")
    except Exception as e:
        errors.append(f"❌ 练习2 查用户 todos 报错：{e}")

    # ---- 练习 3：INNER JOIN 查单个 ----
    try:
        row = get_todo_owner(conn, 1)
        if row != ("买牛奶", "alice"):
            errors.append(f"❌ 练习3 查单条：期望 ('买牛奶', 'alice')，实际 {row}")
        row_none = get_todo_owner(conn, 999)
        if row_none is not None:
            errors.append(f"❌ 练习3 查单条：查不到应返回 None，实际 {row_none}")
    except Exception as e:
        errors.append(f"❌ 练习3 查单条报错：{e}")

    # ---- 练习 4：LEFT JOIN 找没 todo 的用户 ----
    try:
        rows = get_users_without_todos(conn)
        if rows != ["carol"]:
            errors.append(f"❌ 练习4 LEFT JOIN 找缺失：期望 ['carol']，实际 {rows}")
    except Exception as e:
        errors.append(f"❌ 练习4 LEFT JOIN 找缺失报错：{e}")

    # ---- 练习 5：LEFT JOIN + GROUP BY 聚合 ----
    try:
        rows = count_todos_per_user(conn)
        expected = [("alice", 2), ("bob", 1), ("carol", 0)]
        if rows != expected:
            errors.append(f"❌ 练习5 聚合统计：期望 {expected}，实际 {rows}")
    except Exception as e:
        errors.append(f"❌ 练习5 聚合统计报错：{e}")

    # ---- 练习 6：RIGHT JOIN ----
    try:
        rows = right_join_all_todos(conn)
        expected = [("买牛奶", "alice"), ("写代码", "alice"), ("开会", "bob"), ("孤儿任务", None)]
        if rows != expected:
            errors.append(f"❌ 练习6 RIGHT JOIN：期望 {expected}，实际 {rows}")
    except Exception as e:
        errors.append(f"❌ 练习6 RIGHT JOIN 报错：{e}")

    # 清理
    conn.execute("DROP TABLE IF EXISTS todos")
    conn.execute("DROP TABLE IF EXISTS users")
    conn.close()

    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！JOIN = ✅")
