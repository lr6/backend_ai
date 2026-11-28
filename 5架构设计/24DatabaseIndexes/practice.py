"""
第五阶段 · 学习项 24 Database Indexes — B-Tree、EXPLAIN ANALYZE 检验练习

前置条件（已经帮你配好）：
  1. PostgreSQL 服务已启动
  2. 练习库 index_practice_db 已创建
  3. big_todos 表 100 万行数据已灌好
  4. psycopg 已安装到 .venv

你需要：在每个函数的 TODO 处补全代码。
写完后运行: .venv/bin/python practice.py
全部通过 = 学习项 24 过关 ✅

============================================
 练习数据长什么样（看懂再动手）
============================================
 表 big_todos：100 万行
   id         1 .. 1000000
   user_id    1 .. 10000，每个 user 正好 100 行
   done       true 990000 行 / false 10000 行（每 100 行才有 1 个 false）
   title      'item-<id>'，例如 id=500 → 'item-500'
   created_at 从 2026-01-01 起，每秒一行

 psycopg 工具提醒（不是答案）：
   - connect(..., autocommit=True)：每条语句立刻生效，不用 commit
   - conn.execute(sql) 返回 cursor，fetchall() 拿所有行
   - EXPLAIN 的输出是多行，每行只有一列文本
"""

import re

import psycopg

RAWURL = "dbname=index_practice_db"


# ============================================
# 已提供：连接 + 数据准备（不要改）
# ============================================
def connect():
    """开一个 autocommit 连接（DDL 和 EXPLAIN 都立刻生效）。"""
    return psycopg.connect(RAWURL, autocommit=True)


def ensure_data(conn):
    """确保 big_todos 有 100 万行；没有就灌进去。只跑一次，之后是 no-op。"""
    count = conn.execute("SELECT count(*) FROM big_todos").fetchone()[0]
    if count == 0:
        conn.execute("""
            INSERT INTO big_todos (user_id, done, title, created_at)
            SELECT (g % 10000) + 1,
                   (g % 100) <> 0,
                   'item-' || g,
                   timestamptz '2026-01-01 00:00:00+00' + (g || ' seconds')::interval
            FROM generate_series(1, 1000000) AS g
        """)
    conn.execute("ANALYZE big_todos")


def drop_indexes(conn, *names):
    """删除若干索引（不存在也不报错）。"""
    for name in names:
        conn.execute(f"DROP INDEX IF EXISTS {name}")


# ============================================
# 练习 1：生成执行计划 —— EXPLAIN ANALYZE
# ============================================
def plan_text(conn, sql):
    """
    执行 EXPLAIN (ANALYZE, FORMAT TEXT) + sql，把整个计划拼成一个字符串返回
    （每行之间用 \\n 连接）。

    例如: plan_text(conn, "SELECT * FROM big_todos WHERE user_id = 42")
          → 'Seq Scan on big_todos ...\\nPlanning Time: ...\\nExecution Time: ...'

    提示：
      - EXPLAIN 的输出是多行，每行只有一列文本
      - 别用 FORMAT JSON，文本版更好读
    """
    cur = conn.execute("EXPLAIN (ANALYZE, FORMAT TEXT) " + sql)
    rows = cur.fetchall()
    lines = [row[0] for row in rows]
    return "\n".join(lines)



# ============================================
# 练习 2：读计划 —— 估算行数 vs 实际行数
# ============================================
def plan_rows(conn, sql):
    """
    从执行计划里读出「估算行数」和「实际行数」，返回 (估算, 实际)。
    只看计划的第一行（最外层节点）。

    例如: plan_rows(conn, "SELECT * FROM big_todos WHERE user_id = 42")
          → (约 100, 100)

    提示：
      - 第一行形如:
        Gather  (cost=1000.00..13571.33 rows=100 width=28)
                (actual time=1.008..42.540 rows=100 loops=1)
      - 先出现的 rows= 是估算；actual time=... rows= 里的才是实际
      - 正则提示: r"rows=(\\d+)" 和 r"actual time=[\\d.]+\\.[\\d.]+ rows=(\\d+)"
    """
    text = plan_text(conn, sql)
    first = text.splitlines()[0]
    estimated = int(re.search(r"rows=(\d+)", first).group(1))
    actual = int(re.search(r"actual time=[\d.]+\.\.[\d.]+ rows=(\d+)", first).group(1))
    return (estimated, actual)


# ============================================
# 练习 3：判断一条 SQL 有没有走索引
# ============================================
def uses_index(conn, sql):
    """
    这条 SQL 的执行计划用到索引了吗？返回 True / False。

    判定方法：计划文本里出现以下节点名之一，就算用了索引：
      - Index Scan
      - Bitmap Index Scan
      - Index Only Scan
    （Seq Scan / Parallel Seq Scan = 全表扫描，没走索引）

    例如: uses_index(conn, "SELECT * FROM big_todos WHERE user_id = 42")
          → 取决于当前有没有建对应的索引
    """
    text = plan_text(conn, sql)
    return "Index Scan" in text or "Index Only Scan" in text


# ============================================
# 练习 4：亲手建索引，对比前后
# ============================================
def index_on_user_id(conn):
    """
    体验一次「建索引前后」的差别。

    步骤：
      1) 用 drop_indexes 删掉 idx_bt_user_id 和 idx_bt_user_done
      2) ANALYZE big_todos
      3) before = uses_index(conn, "SELECT * FROM big_todos WHERE user_id = 42")
      4) CREATE INDEX idx_bt_user_id ON big_todos(user_id)
      5) ANALYZE big_todos
      6) after = 再测同一条 SQL
    返回 (before, after)

    预期: (False, True)
    """
    drop_indexes(conn, "idx_bt_user_id", "idx_bt_user_done")
    conn.execute("ANALYZE big_todos")

    sql = "SELECT * FROM big_todos WHERE user_id = 42"
    before = uses_index(conn, sql)

    conn.execute("CREATE INDEX idx_bt_user_id ON big_todos(user_id)")
    conn.execute("ANALYZE big_todos")
    after = uses_index(conn, sql)

    return (before, after)


# ============================================
# 练习 5：选择性 —— 同样的索引，为什么一个用一个不用
# ============================================
def selectivity(conn):
    """
    选择性实验：都在 done 条件上，99% 命中 vs 1% 命中。

    步骤：
      1) 删掉 idx_bt_user_id、idx_bt_done、idx_bt_user_done
      2) CREATE INDEX idx_bt_done ON big_todos(done)
      3) ANALYZE big_todos
      4) 返回 (是否走索引: WHERE done = true,
               是否走索引: WHERE done = false)

    预期: (False, True)
    想一想：两边行数差 99 倍，为什么结果反过来？
    """
    drop_indexes(conn, "idx_bt_user_id", "idx_bt_done", "idx_bt_user_done")
    conn.execute("CREATE INDEX idx_bt_done ON big_todos(done)")
    conn.execute("ANALYZE big_todos")

    return (
        uses_index(conn, "SELECT * FROM big_todos WHERE done = true"),
        uses_index(conn, "SELECT * FROM big_todos WHERE done = false"),
    )


# ============================================
# 练习 6：复合索引的最左前缀
# ============================================
def leftmost_prefix(conn):
    """
    复合索引 (user_id, done) 的「最左前缀」规则。

    步骤：
      1) 删掉 idx_bt_user_id、idx_bt_done、idx_bt_user_done
      2) CREATE INDEX idx_bt_user_done ON big_todos(user_id, done)
      3) ANALYZE big_todos
      4) 返回 (是否走索引: WHERE user_id = 42,
               是否走索引: WHERE done = false)

    预期: (True, False)
    想一想：索引里先按 user_id 排、再按 done 排，第二条为什么用不上？
    """
    drop_indexes(conn, "idx_bt_user_id", "idx_bt_done", "idx_bt_user_done")
    conn.execute("CREATE INDEX idx_bt_user_done ON big_todos(user_id, done)")
    conn.execute("ANALYZE big_todos")

    return (
        uses_index(conn, "SELECT * FROM big_todos WHERE user_id = 42"),
        uses_index(conn, "SELECT * FROM big_todos WHERE done = false"),
    )


# ============================================
# 练习 7：给列套函数，索引就废了
# ============================================
def function_kills_index(conn):
    """
    条件里给列套上一个函数，还能用上索引吗？

    步骤：
      1) 删掉 idx_bt_title，再 CREATE INDEX idx_bt_title ON big_todos(title)
      2) ANALYZE big_todos
      3) 返回 (是否走索引: WHERE title = 'item-500',
               是否走索引: WHERE lower(title) = 'item-500')

    预期: (True, False)
    """
    drop_indexes(conn, "idx_bt_title")
    conn.execute("CREATE INDEX idx_bt_title ON big_todos(title)")
    conn.execute("ANALYZE big_todos")

    return (
        uses_index(conn, "SELECT * FROM big_todos WHERE title = 'item-500'"),
        uses_index(conn, "SELECT * FROM big_todos WHERE lower(title) = 'item-500'"),
    )


# ============================================
# 练习 8：ORDER BY + LIMIT 也很吃索引
# ============================================
def order_by_limit(conn):
    """
    ORDER BY + LIMIT 没有索引时，数据库必须把 100 万行排完序再取前 10 条。

    步骤：
      1) 删掉 idx_bt_created
      2) ANALYZE big_todos
      3) before = 是否走索引:
         SELECT * FROM big_todos ORDER BY created_at LIMIT 10
      4) CREATE INDEX idx_bt_created ON big_todos(created_at)
      5) ANALYZE big_todos
      6) after = 再测一次
    返回 (before, after)

    预期: (False, True)
    """
    drop_indexes(conn, "idx_bt_created")
    conn.execute("ANALYZE big_todos")

    sql = "SELECT * FROM big_todos ORDER BY created_at LIMIT 10"
    before = uses_index(conn, sql)

    conn.execute("CREATE INDEX idx_bt_created ON big_todos(created_at)")
    conn.execute("ANALYZE big_todos")
    after = uses_index(conn, sql)

    return (before, after)


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []
    conn = connect()
    ensure_data(conn)

    def run(label, fn, expected):
        try:
            actual = fn()
        except Exception as e:
            actual = f"{type(e).__name__}: {e}"
        if actual == expected:
            print(f"✅ {label}")
        else:
            errors.append(f"❌ {label}: 期望 {expected!r}，实际 {actual!r}")
            print(f"❌ {label}: 期望 {expected!r}，实际 {actual!r}")

    # 练习 1：计划文本
    def test_plan_text():
        text = plan_text(conn, "SELECT * FROM big_todos WHERE user_id = 42")
        return (
            isinstance(text, str)
            and "Execution Time" in text
            and "rows=" in text
        )

    run("练习 1 plan_text", test_plan_text, True)

    # 练习 2：估算 vs 实际
    def test_plan_rows():
        est, actual = plan_rows(conn, "SELECT * FROM big_todos WHERE user_id = 42")
        return (50 <= est <= 200, actual)

    run("练习 2 plan_rows", test_plan_rows, (True, 100))

    # 练习 3：判断是否走索引（当前没有 user_id 索引 → 应为 False）
    def test_uses_index():
        drop_indexes(conn, "idx_bt_user_id", "idx_bt_user_done")
        conn.execute("ANALYZE big_todos")
        return uses_index(conn, "SELECT * FROM big_todos WHERE user_id = 42")

    run("练习 3 uses_index", test_uses_index, False)

    # 练习 4：建索引前后
    run("练习 4 index_on_user_id", lambda: index_on_user_id(conn), (False, True))

    # 练习 5：选择性
    run("练习 5 selectivity", lambda: selectivity(conn), (False, True))

    # 练习 6：最左前缀
    run("练习 6 leftmost_prefix", lambda: leftmost_prefix(conn), (True, False))

    # 练习 7：函数包裹列
    run("练习 7 function_kills_index", lambda: function_kills_index(conn), (True, False))

    # 练习 8：ORDER BY + LIMIT
    run("练习 8 order_by_limit", lambda: order_by_limit(conn), (False, True))

    if errors:
        print(f"\n有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("\n🎉 全部通过！学习项 24 Database Indexes = ✅")
