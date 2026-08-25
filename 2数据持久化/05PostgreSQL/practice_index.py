"""
第二阶段 · 5 PostgreSQL — 索引（Index）检验练习

前置条件：PostgreSQL 已启动、todo_db 已创建、psycopg 已装。

本轮聚焦「索引」：建索引、查索引、删索引、用 EXPLAIN 看执行计划。

写完运行: .venv/bin/python practice_index.py
全部通过 = 索引过关 ✅

============================================
 psycopg 用法速查（同前几课）
============================================
  conn.execute(sql)              执行 SQL，返回 cursor
  conn.execute(sql, (参数,))     参数化（%s 占位符）
  cur.fetchone()                 取一行（tuple 或 None）
  cur.fetchall()                 取所有行（list[tuple]）

  索引相关 SQL 骨架:
    CREATE INDEX 索引名 ON 表名(列名)
    DROP INDEX 索引名
    SELECT indexname FROM pg_indexes WHERE tablename = '表名'
    EXPLAIN SELECT ...           查看执行计划
"""

import psycopg

CONN_STRING = "dbname=todo_db"


def get_conn():
    """返回一个已连接的数据库连接（自动提交）。不用改。"""
    return psycopg.connect(CONN_STRING, autocommit=True)


# ===== 练习 1：查某张表的所有索引 =====
def list_indexes(conn, table_name):
    """
    查出某张表的所有索引名，按名字升序返回列表（list of str）。
    例如: list_indexes(conn, "users") → ['users_pkey', ...]

    提示：用 pg_indexes 视图 —— SELECT indexname FROM pg_indexes WHERE tablename = %s
    """
    # TODO
    cur = conn.execute("SELECT indexname FROM pg_indexes WHERE tablename = %s", (table_name,))
    return [x[0] for x in cur.fetchall()]


# ===== 练习 2：判断索引是否存在 =====
def index_exists(conn, index_name):
    """
    判断某个名字的索引是否存在，返回 True/False。
    例如: index_exists(conn, "users_pkey") → True（主键自动建的索引）

    提示：用 pg_indexes 查，有结果返回 True，没结果返回 False。
    """
    # TODO
    cur = conn.execute("SELECT indexname FROM pg_indexes WHERE indexname = %s", (index_name,))
    arr = [x[0] for x in cur.fetchall()]
    if index_name in arr:
        return True
    else:
        return False


# ===== 练习 3：建索引 =====
def create_user_id_index(conn):
    """
    给 todos 表的 user_id 列建一个索引，索引名叫 idx_todos_user_id。
    建完后返回索引名（字符串 "idx_todos_user_id"）。

    提示：CREATE INDEX idx_todos_user_id ON todos(user_id)
    """
    # TODO
    conn.execute("CREATE INDEX idx_todos_user_id ON todos(user_id)")
    return 'idx_todos_user_id'


# ===== 练习 4：用 EXPLAIN 看执行计划 =====
def get_scan_type(conn, query):
    """
    用 EXPLAIN 查看 query 的执行计划，判断用的是哪种扫描：
      - 计划里出现 "Index"（索引扫描）→ 返回 "index"
      - 否则（全表扫描 Seq Scan）→ 返回 "seq"

    例如: get_scan_type(conn, "SELECT * FROM todos WHERE user_id = 1") → "index"

    提示：
      1. conn.execute("EXPLAIN " + query) 拿回计划
      2. fetchall() 得到多行文本，每行是 (文本,) 的 tuple
      3. 把所有行拼成一个字符串，看里面有没有 "Index"
    """
    # TODO
    cur = conn.execute("EXPLAIN " + query)
    arr = [x[0] for x in cur.fetchall()]
    plan = ' '.join(arr)
    if 'Index' in plan:
        return 'index'
    else:
        return 'seq'


# ===== 练习 5：删索引 =====
def drop_index(conn, index_name):
    """
    删除指定名字的索引。删除成功返回 True，失败（如索引不存在）返回 False。

    提示：
      try:
          conn.execute(f"DROP INDEX {index_name}")
          return True
      except Exception:
          return False
    """
    # TODO
    try:
        conn.execute(f'DROP INDEX {index_name}')
        return True
    except Exception:
        return False


# ===== 练习 6：概念——哪些列该建索引 =====
def should_index(column_name):
    """
    判断某列「值不值得」建索引，返回 True/False。
    简化规则：
      - 经常出现在 WHERE / JOIN ON 里的列 → 值得建（True）
      - 很少被查询过滤、或区分度极低的列 → 不值得（False）

    已知场景（按这个判断）：
      - "user_id"  → JOIN 的 ON 列，经常查        → True
      - "username" → 登录时 WHERE 查              → True
      - "title"    → 很少按标题过滤               → False
      - "done"     → 只有 true/false，区分度太低   → False
    """
    # TODO
    if column_name in ['user_id', 'username']:
        return True
    else:
        return False


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
            user_id INTEGER
        )
    """)
    # 插入 20000 条 todo（user_id 在 1~100 分布），让 EXPLAIN 测试有足够数据
    conn.execute("""
        INSERT INTO todos (title, user_id)
        SELECT 'todo ' || i, (i % 100) + 1
        FROM generate_series(1, 20000) AS i
    """)

    # ---- 练习 1：list_indexes ----
    try:
        idxs = list_indexes(conn, "users")
        if "users_pkey" not in idxs:
            errors.append(f"❌ 练习1 查索引：users 表应包含主键索引 users_pkey，实际 {idxs}")
    except Exception as e:
        errors.append(f"❌ 练习1 查索引报错：{e}")

    # ---- 练习 2：index_exists ----
    try:
        if index_exists(conn, "users_pkey") is not True:
            errors.append("❌ 练习2 判断存在：users_pkey 应该存在（主键自动建的）")
        if index_exists(conn, "不存在的索引") is not False:
            errors.append("❌ 练习2 判断存在：不存在的索引应返回 False")
    except Exception as e:
        errors.append(f"❌ 练习2 判断存在报错：{e}")

    # ---- 练习 3：create_user_id_index ----
    try:
        name = create_user_id_index(conn)
        if name != "idx_todos_user_id":
            errors.append(f"❌ 练习3 建索引：应返回 'idx_todos_user_id'，实际 {name}")
        if index_exists(conn, "idx_todos_user_id") is not True:
            errors.append("❌ 练习3 建索引：索引没建成功（index_exists 返回 False）")
    except Exception as e:
        errors.append(f"❌ 练习3 建索引报错：{e}")

    # ---- 练习 4：get_scan_type ----
    try:
        # 强制规划器用索引（否则数据太少可能选全表扫描），这是看索引效果的标准手法
        conn.execute("SET enable_seqscan = off")
        scan = get_scan_type(conn, "SELECT * FROM todos WHERE user_id = 50")
        if scan != "index":
            errors.append(f"❌ 练习4 EXPLAIN：建了索引后应走 'index'，实际 {scan}")
    except Exception as e:
        errors.append(f"❌ 练习4 EXPLAIN 报错：{e}")

    # ---- 练习 5：drop_index ----
    try:
        if drop_index(conn, "idx_todos_user_id") is not True:
            errors.append("❌ 练习5 删索引：删除存在的索引应返回 True")
        if index_exists(conn, "idx_todos_user_id") is not False:
            errors.append("❌ 练习5 删索引：删完索引应该不存在了")
        if drop_index(conn, "不存在的索引") is not False:
            errors.append("❌ 练习5 删索引：删除不存在的索引应返回 False")
    except Exception as e:
        errors.append(f"❌ 练习5 删索引报错：{e}")

    # ---- 练习 6：should_index ----
    try:
        cases = {
            "user_id": True,
            "username": True,
            "title": False,
            "done": False,
        }
        for col, expected in cases.items():
            got = should_index(col)
            if got != expected:
                errors.append(f"❌ 练习6 概念判断：{col} 期望 {expected}，实际 {got}")
    except Exception as e:
        errors.append(f"❌ 练习6 概念判断报错：{e}")

    # 清理
    conn.execute("DROP TABLE IF EXISTS todos")
    conn.execute("DROP TABLE IF EXISTS users")
    conn.close()

    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！索引 = ✅")
