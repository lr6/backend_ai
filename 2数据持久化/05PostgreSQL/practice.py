"""
第二阶段 · 5 PostgreSQL — SQL 基础（CRUD）检验练习

前置条件（已经帮你配好）：
  1. PostgreSQL 服务已启动
  2. 数据库 todo_db 已创建
  3. psycopg 驱动已安装到 .venv

你需要：在每个函数的 TODO 处，用 psycopg 执行 SQL 完成操作。

写完运行: .venv/bin/python practice.py
全部通过 = SQL CRUD 过关 ✅

============================================
 psycopg 用法速查（工具用法，不是答案）
============================================
  conn.execute(sql)              执行一条 SQL，返回 cursor
  conn.execute(sql, (参数,))     带参数执行（%s 是占位符）
  cur.fetchone()                 取第一行，返回 tuple 或 None
  cur.fetchall()                 取所有行，返回 list[tuple]
  cur.rowcount                   上一条语句影响的行数

  参数化示例（防 SQL 注入，注意 %s + 元组）:
      conn.execute("SELECT * FROM t WHERE name = %s", ("小明",))
"""

import psycopg

CONN_STRING = "dbname=todo_db"


def get_conn():
    """返回一个已连接的数据库连接（自动提交）。不用改。"""
    return psycopg.connect(CONN_STRING, autocommit=True)


# ===== 练习 1：建表（CREATE TABLE） =====
def create_table(conn):
    """
    创建 todos 表，包含三列：
      - id    : 自增整数主键   SERIAL PRIMARY KEY
      - title : 文本，不能为空  TEXT NOT NULL
      - done  : 布尔，默认 false  BOOLEAN DEFAULT false

    执行后表 todos 存在即可，不需要返回值。
    """
    # TODO: 写 CREATE TABLE 语句并执行
    conn.execute("""CREATE TABLE todos (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        done BOOLEAN DEFAULT false
    )""")


# ===== 练习 2：插入（INSERT INTO） =====
def insert_todo(conn, title):
    """
    向 todos 表插入一条记录，title 用参数传入，done 用默认值(false)。
    返回新插入这一行的 id。
    例如: insert_todo(conn, "买牛奶") → 1

    提示：
      1. INSERT INTO todos (title) VALUES (%s)
      2. 结尾加 RETURNING id 能拿到自增的 id
      3. 用 fetchone()[0] 取出这个 id
    """
    # TODO
    cur = conn.execute('INSERT INTO todos (title) VALUES (%s) RETURNING id', (title,))
    return cur.fetchone()[0]




# ===== 练习 3：查询全部（SELECT） =====
def get_all_todos(conn):
    """
    查询 todos 表里所有行，按 id 升序。
    返回所有行（list of tuple）。
    例如: [(1, '买牛奶', False), (2, '写代码', False)]

    提示：SELECT * FROM ... ORDER BY id
    """
    # TODO
    cur = conn.execute('SELECT * FROM todos ORDER BY id')
    return cur.fetchall()


# ===== 练习 4：条件查询（SELECT + WHERE） =====
def get_unfinished_todos(conn):
    """
    只查询 done = false（未完成）的行，按 id 升序。
    返回所有未完成的行（list of tuple）。

    提示：SELECT * FROM ... WHERE done = false ORDER BY id
    """
    # TODO
    cur = conn.execute('SELECT * FROM todos WHERE done = false ORDER BY id')
    return cur.fetchall()


# ===== 练习 5：更新（UPDATE） =====
def mark_todo_done(conn, todo_id):
    """
    把指定 id 的 todo 标记为完成（done = true）。
    返回受影响的行数（0 或 1）。

    提示：
      1. UPDATE todos SET done = true WHERE id = %s
      2. 用 cur.rowcount 拿受影响的行数
    """
    # TODO
    cur = conn.execute('UPDATE todos SET done = true WHERE id = %s', (todo_id,))
    return cur.rowcount


# ===== 练习 6：删除（DELETE） =====
def delete_todo(conn, todo_id):
    """
    删除指定 id 的 todo。
    返回受影响的行数（0 或 1）。

    提示：DELETE FROM todos WHERE id = %s
    """
    # TODO
    cur = conn.execute('DELETE FROM todos WHERE id = %s', (todo_id,))
    return cur.rowcount


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []
    conn = get_conn()

    # 每次运行从头开始，保证可重复
    conn.execute("DROP TABLE IF EXISTS todos")

    # ---- 练习 1：create_table ----
    try:
        create_table(conn)
        rows = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'todos'"
        ).fetchall()
        cols = {r[0] for r in rows}
        if cols != {"id", "title", "done"}:
            errors.append(f"❌ 练习1 建表：列不对，期望 {{id, title, done}}，实际 {cols}")
    except Exception as e:
        errors.append(f"❌ 练习1 建表报错：{e}")

    # ---- 练习 2：insert_todo ----
    id1 = id2 = None
    try:
        id1 = insert_todo(conn, "买牛奶")
        id2 = insert_todo(conn, "写代码")
        if id1 != 1 or id2 != 2:
            errors.append(f"❌ 练习2 插入：期望 id 为 1 和 2，实际 {id1} 和 {id2}")
        row = conn.execute("SELECT title, done FROM todos WHERE id = %s", (id1,)).fetchone()
        if row != ("买牛奶", False):
            errors.append(f"❌ 练习2 插入：内容不对，期望 ('买牛奶', False)，实际 {row}")
    except Exception as e:
        errors.append(f"❌ 练习2 插入报错：{e}")

    # ---- 练习 3：get_all_todos ----
    try:
        all_todos = get_all_todos(conn)
        if len(all_todos) != 2:
            errors.append(f"❌ 练习3 查询全部：期望 2 条，实际 {len(all_todos)} 条")
        elif all_todos[0][1] != "买牛奶" or all_todos[1][1] != "写代码":
            errors.append(f"❌ 练习3 查询全部：顺序或内容不对，实际 {all_todos}")
    except Exception as e:
        errors.append(f"❌ 练习3 查询全部报错：{e}")

    # ---- 练习 4：get_unfinished_todos ----
    try:
        unfinished = get_unfinished_todos(conn)
        if len(unfinished) != 2:
            errors.append(f"❌ 练习4 条件查询：期望 2 条未完成，实际 {len(unfinished)} 条")
    except Exception as e:
        errors.append(f"❌ 练习4 条件查询报错：{e}")

    # ---- 练习 5：mark_todo_done ----
    try:
        n = mark_todo_done(conn, id1)
        if n != 1:
            errors.append(f"❌ 练习5 更新：期望影响 1 行，实际 {n}")
        done = conn.execute("SELECT done FROM todos WHERE id = %s", (id1,)).fetchone()[0]
        if not done:
            errors.append(f"❌ 练习5 更新：id={id1} 的 done 应为 True，实际 {done}")
        unfinished = get_unfinished_todos(conn)
        if len(unfinished) != 1:
            errors.append(f"❌ 练习5 更新：更新后未完成应剩 1 条，实际 {len(unfinished)} 条")
    except Exception as e:
        errors.append(f"❌ 练习5 更新报错：{e}")

    # ---- 练习 6：delete_todo ----
    try:
        n = delete_todo(conn, id2)
        if n != 1:
            errors.append(f"❌ 练习6 删除：期望影响 1 行，实际 {n}")
        remaining = get_all_todos(conn)
        if len(remaining) != 1:
            errors.append(f"❌ 练习6 删除：删除后应剩 1 条，实际 {len(remaining)} 条")
    except Exception as e:
        errors.append(f"❌ 练习6 删除报错：{e}")

    # 清理
    conn.execute("DROP TABLE IF EXISTS todos")
    conn.close()

    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！SQL CRUD = ✅")
