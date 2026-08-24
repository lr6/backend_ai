# 5 PostgreSQL — SQL 基础（CRUD）笔记

> 学习日期：2026-08-24
> 状态：学习项 5 进行中（本笔记覆盖「SQL 基础」部分；表设计、JOIN、索引待学）

---

## 一、知识点讲解

### 1. PostgreSQL 是什么（前端类比）

前端存数据的方式：`localStorage`（换电脑就没了）、内存变量（刷新就没了）。后端需要数据**长期存住、结构清晰、能高效查询、并发访问不打架**——这就是数据库。

PostgreSQL 是**关系型数据库**，数据存在一张张**表（table）**里：

| 数据库概念 | 前端类比 |
|-----------|---------|
| 表（table） | `array<object>`（结构预先定义好） |
| 列（column） | 对象的 key |
| 行（row） | 数组里的一个对象 |
| 关系（外键） | 对象之间的引用（后面学） |

层级：**数据库（database）→ 表（table）→ 列（column）/ 行（row）**。

### 2. ⭐ 核心认知：SQL 在 Python 里是「字符串」，不是「代码」

这是从 0 到 1 最关键的一点。**Python 解释器不懂 SQL**，SQL 是给「数据库」听的。

- SQL 必须用**引号包成字符串**，再传给 `conn.execute(sql)` 执行。
- `conn.execute(sql)` 就像前端的 `fetch(url, {body})`——SQL 字符串是「数据」，`conn.execute` 是「发请求」，数据库才是「执行者」。

```python
# ❌ 错误：把 SQL 当 Python 代码直接写
CREATE TABLE todos (...)

# ✅ 正确：SQL 是字符串，用 conn.execute 发给数据库
conn.execute("CREATE TABLE todos (...)")
```

### 3. CRUD 五语句（对照昨天的数组写法）

| 操作 | 昨天的数组写法 | SQL 写法 |
|------|--------------|---------|
| 建表 | （无，数组不用声明结构） | `CREATE TABLE` |
| 增 Create | `todos.append(...)` | `INSERT INTO` |
| 查 Read | `[t for t in todos if ...]` | `SELECT ... WHERE ...` |
| 改 Update | `todo.done = True` | `UPDATE ... SET ... WHERE ...` |
| 删 Delete | `todos.remove(todo)` | `DELETE ... WHERE ...` |

语法骨架：

```sql
CREATE TABLE todos (
    id    SERIAL PRIMARY KEY,       -- 自增主键
    title TEXT NOT NULL,            -- 不能为空
    done  BOOLEAN DEFAULT false     -- 默认 false
);

INSERT INTO todos (title) VALUES ('买牛奶');          -- 增
SELECT * FROM todos;                                 -- 查全部
SELECT * FROM todos WHERE done = false;              -- 条件查
UPDATE todos SET done = true WHERE id = 1;           -- 改
DELETE FROM todos WHERE id = 1;                      -- 删
```

### 4. cursor ≠ 数据（要 fetch 才拿到数据）

`conn.execute(sql)` 返回的是 **cursor（游标）对象**，它只是「**握住**」了查询结果，还没取出来。

| 方法 | 作用 | 返回 |
|------|------|------|
| `cur.fetchall()` | 取**所有**行 | `list[tuple]` |
| `cur.fetchone()` | 取**一行** | `tuple` 或 `None` |

前端类比：`conn.execute` ≈ `fetch()` 返回 `res`（Response 对象），`cur.fetchall()` ≈ `res.json()`（这一步才拿到真正的数据）。

### 5. 参数化（防 SQL 注入）

用 `%s` 占位符 + 元组传参，**不要用 f-string 拼 SQL**：

```python
conn.execute("SELECT * FROM todos WHERE id = %s", (todo_id,))   # ✅
conn.execute(f"SELECT * FROM todos WHERE id = {todo_id}")         # ❌ 注入风险
```

> `(todo_id,)` 的逗号不能丢，否则是普通括号不是元组。

### 6. rowcount：改/删后拿「影响了几行」

```python
cur = conn.execute("UPDATE todos SET done = true WHERE id = %s", (todo_id,))
cur.rowcount   # 0 或 1，是属性不是方法（不加括号）
```

---

## 二、练习 ↔ 知识点映射

| 练习 | 函数 | 知识点 |
|------|------|--------|
| 1 | `create_table` | `CREATE TABLE` 建表、`SERIAL`/`PRIMARY KEY`/`TEXT`/`BOOLEAN`、列之间逗号 |
| 2 | `insert_todo` | `INSERT INTO` + 参数化 `%s` + `RETURNING id` + `fetchone()[0]` |
| 3 | `get_all_todos` | `SELECT *` + `ORDER BY id` + `fetchall()` |
| 4 | `get_unfinished_todos` | `SELECT` + `WHERE done = false` + `fetchall()` |
| 5 | `mark_todo_done` | `UPDATE` + `SET` + `WHERE id = %s` + `rowcount` |
| 6 | `delete_todo` | `DELETE` + `WHERE id = %s` + `rowcount` |

---

## 三、练习纠错全记录

### 第 1 轮：把 SQL 当 Python 代码写（最核心的认知错误）

**现象**：练习 1、2 写成了这样——

```python
def create_table(conn):
    CREATE TABLE todos (          # 没引号、没 conn.execute
        id SERIAL PRIMARY KEY
        ...
    )

def insert_todo(conn, title):
    return INSERT INTO todos ...  # return 后面跟 SQL
```

**原因**：还没建立「SQL 是字符串，Python 只是传话的」这个认知。以为 SQL 能像 Python 代码一样直接写。

**对应知识点**：核心认知（知识点 2）。

**解决**：SQL 用引号包成字符串 → `conn.execute(sql)` 执行；`return` 的不是 SQL，而是执行后取到的结果。

### 第 2 轮：两个拼写笔误

**现象**：
- 练习 1：`conn.execuye(...)` —— `execute` 多打了个 `u`
- 练习 2：`'NSERT INTO ...'` —— `INSERT` 少了开头的 `I`

**原因**：纯笔误（typo），结构已对。

**解决**：`execute` / `INSERT` 拼对即可。

### 第 3 轮：`return cur` 忘了 `fetchall()`

**现象**：练习 3、4 写成 `return cur`（返回了 cursor 对象，不是数据行）。

**原因**：以为 `conn.execute()` 直接返回数据，没意识到返回的是 cursor。

**对应知识点**：cursor ≠ 数据（知识点 4）。

**解决**：`return cur.fetchall()`。

---

## 四、踩坑速查表

| 错误写法 | 报错 / 现象 | 正确写法 |
|---------|------------|---------|
| 裸写 `CREATE TABLE ...` 不加引号、不 `conn.execute` | `SyntaxError: invalid syntax` | `conn.execute("""CREATE TABLE ...""")` |
| `conn.execuye(...)` | `AttributeError: ... has no attribute 'execuye'` | `conn.execute(...)` |
| `'NSERT INTO ...'` | 数据库 syntax error | `'INSERT INTO ...'` |
| `return cur`（查询后忘 `fetchall`） | 返回 cursor 对象，比对失败 | `return cur.fetchall()` |
| `(title)` 没逗号 | 不是元组，参数化报错 | `(title,)` |
| `UPDATE`/`DELETE` 不带 `WHERE` | 影响整张表（数据灾难） | 一定带 `WHERE` |
| 字符串用双引号 `"买牛奶"` | 双引号代表列名，报错 | 用单引号 `'买牛奶'` |

---

## 五、环境备忘（本次会话搭好的）

- PostgreSQL 16 安装：`brew install postgresql@16`
- 启动服务：`brew services start postgresql@16`
- 数据库 `todo_db` 已创建
- Python 驱动：`psycopg` 3.x（装进 `.venv`）
- 连接串：`dbname=todo_db`
- 运行练习：项目根目录 `.venv/bin/python 2数据持久化/05PostgreSQL/practice.py`
