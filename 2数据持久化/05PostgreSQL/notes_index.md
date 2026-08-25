# 5 PostgreSQL — 索引（Index）笔记

> 学习日期：2026-08-25
> 状态：✅ **学习项 5 PostgreSQL 全部完成**（SQL CRUD、表设计、JOIN、索引）

---

## 一、知识点讲解

### 1. 索引是什么：给查找加个「目录」

没有索引时，`WHERE user_id = 50` 要**全表扫描**（一行行找）。索引给某列建一个 **B-Tree（平衡树）**，数据库自动维护，查这列时走树查找，直接定位。

**前端类比**（核心）：

```javascript
// 没有索引：全表扫描，一行行找 → O(n)
todos.find(t => t.user_id === 50)

// 有索引：直接定位，像 Map 或字典 → O(1) / O(log n)
todosByUserId.get(50)
```

### 2. 该给哪些列建索引

经常出现在这三个位置的列：

1. `WHERE` 条件列 —— `WHERE username = 'alice'`
2. `JOIN` 的 `ON` 列 —— `ON t.user_id = u.id` 里的 `user_id`
3. `ORDER BY` 排序列

### 3. 索引的代价（为什么不能每列都建）

1. **占磁盘空间**（每个索引是额外一棵树）
2. **写操作变慢**：每次 INSERT/UPDATE/DELETE 都要同步更新索引

前端类比：给数组维护一个 Map 索引，读变快，但每次 push/改元素都要同步更新 Map，写变慢。所以只给「查得多的列」建。

### 4. 主键 / UNIQUE 自动建索引

`PRIMARY KEY` 和 `UNIQUE` 约束**自动创建索引**（如 `users_pkey`）。所以按 `id` 查已经很快，不用手动建。要手动建的是外键列（`user_id`）这种。

### 5. EXPLAIN 看执行计划

`EXPLAIN SELECT ...` 显示数据库打算怎么执行：

- **`Seq Scan`** = 顺序扫描（全表扫，慢）
- **`Index Scan`** = 用索引（快）

前端类比：EXPLAIN ≈ `console.time()`，看查询走的哪条路、快不快。

⚠️ **小表陷阱**：数据量很少时，规划器可能选 `Seq Scan`（因为全表扫更快）。要看索引效果，用 `SET enable_seqscan = off` 强制规划器用索引（测试代码里就这么干的）。

### 6. 语法速查

```sql
CREATE INDEX idx_todos_user_id ON todos(user_id);   -- 建索引
DROP INDEX idx_todos_user_id;                        -- 删索引
SELECT indexname FROM pg_indexes WHERE tablename='todos';   -- 查某表的索引
SELECT indexname FROM pg_indexes WHERE indexname='xxx';      -- 判断某索引在不在
```

`pg_indexes` 视图的关键列：
- `tablename` —— 表名（练习 1 按它查）
- `indexname` —— 索引名（练习 2 按它查）

---

## 二、练习 ↔ 知识点映射

| 练习 | 函数 | 知识点 |
|------|------|--------|
| 1 | `list_indexes` | `pg_indexes` 按 `tablename` 查 + 列表推导取 `[0]` |
| 2 | `index_exists` | `pg_indexes` 按 `indexname` 查 + `fetchone()` 判断 |
| 3 | `create_user_id_index` | `CREATE INDEX` 语法 + 返回索引名 |
| 4 | `get_scan_type` | `EXPLAIN` + 拼字符串 + 判断 `Index` |
| 5 | `drop_index` | `DROP INDEX` + try/except |
| 6 | `should_index` | 概念：哪些列值得建索引 |

---

## 三、练习纠错全记录

### 第 1 轮（练习 1、2）

**① 练习 1 `fetchall()` 直接 return（老坑第 3 次）**
- 现象：`return cur.fetchall()` 返回 `[('users_pkey',), ...]`（tuple 列表），题目要 `['users_pkey', ...]`（字符串列表）。
- 原因：`fetchall()` 每行是 tuple，要取 `[0]` 转字符串。
- 解决：`[x[0] for x in cur.fetchall()]`。
- ⚠️ 这个坑在 JOIN 课练习 2、4 都犯过，这里第 3 次——「fetchall 返回 tuple 列表」还没形成稳定认知，务必记牢。

**② 练习 2 概念误解：「不知道表名怎么判断索引」**
- 现象：用户卡住，以为判断索引存在需要表名。
- 原因：不知道 `pg_indexes` 视图里有两列——`tablename`（查某表的索引）和 `indexname`（查某个索引在不在）。
- 解决：判断索引存在按 `indexname` 查，不需要表名。

**③ 练习 2 `pg_index` 拼错**
- 现象：`FROM pg_index WHERE ...`。
- 原因：视图名是 `pg_indexes`（有 es），写成了 `pg_index`。
- 解决：`pg_indexes`。

### 第 2 轮（练习 3、4）

**④ 练习 3 `CREATE` 漏 `INDEX` 关键字**
- 现象：`CREATE idx_todos_user_id ON todos(user_id)`。
- 原因：建索引完整语句是 `CREATE INDEX 索引名 ON 表(列)`，漏了 `INDEX`。
- 解决：`CREATE INDEX idx_todos_user_id ON todos(user_id)`。

**⑤ 练习 3 没 return**
- 现象：只 `execute` 不 `return`，返回 `None`。
- 原因：docstring 要求返回索引名。
- 解决：`return "idx_todos_user_id"`。

**⑥ 练习 4 `arr.join(',')` 用法反了**
- 现象：`arr = cur.fetchall()`（list of tuple），`str1 = arr.join(',')`。
- 原因：① `.join()` 是**字符串**的方法，用法是「分隔符.join(可迭代)」，不是「可迭代.join(分隔符)」；② `arr` 里每项是 tuple，得先取 `[0]`。
- 解决：`" ".join(r[0] for r in rows)`。
- ⚠️ 这是 Python 里 `join` 方向写反的典型错误，前端 JS 是 `arr.join(',')`（数组方法），Python 是 `','.join(arr)`（字符串方法）——**方向相反**，前端思维容易混淆。

---

## 四、踩坑速查表

| 错误写法 | 报错 / 现象 | 正确写法 |
|---------|------------|---------|
| `return cur.fetchall()`（要字符串列表） | 返回 `[('x',), ...]` | `[x[0] for x in cur.fetchall()]` |
| `FROM pg_index` | `relation "pg_index" does not exist` | `FROM pg_indexes` |
| `CREATE 名 ON ...`（漏 INDEX） | SQL 语法错误 | `CREATE INDEX 名 ON ...` |
| `arr.join(',')` | `AttributeError: 'list' object has no attribute 'join'` | `','.join(str_list)` |
| 小表看索引效果 | 走 `Seq Scan` 不走索引 | `SET enable_seqscan = off` |

---

## 五、本次会话用户主动提问的概念点

1. 「练习 2 我不会，都不知道表名，怎么判断索引」→ 澄清 `pg_indexes` 有两列（`tablename` / `indexname`），判断索引存在按 `indexname` 查，不需表名。

## 六、前端思维 vs Python 思维（本次新暴露）

| 操作 | JS 写法 | Python 写法 |
|------|---------|-------------|
| 数组/列表拼接 | `arr.join(',')` | `','.join(arr)`（分隔符在前）|
| 遍历查找 | `arr.find(x => x.id === y)` | `next((x for x in arr if ...), None)` 或循环 |

`join` 方向是本次踩坑的深层原因——JS 是「数组的方法」，Python 是「字符串的方法」，调用主体反过来了。
