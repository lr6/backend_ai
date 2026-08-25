# 5 PostgreSQL — JOIN（多表关联查询）笔记

> 学习日期：2026-08-25
> 状态：学习项 5 进行中（本笔记覆盖「JOIN」部分；索引待学）

---

## 一、知识点讲解

### 1. 为什么需要 JOIN：数据拆开后要「合并」

表设计把数据拆成 `users`、`todos` 两张表（外键关联），但查询「每个 todo 是谁建的」要同时拿两张表的数据。JOIN 就是干这个。

**前端类比**：两个数组通过 key 合并：

```js
const users = [{ id: 1, username: 'alice' }, { id: 2, username: 'bob' }]
const todos = [{ title: '买牛奶', user_id: 1 }, { title: '写代码', user_id: 1 }]

todos.map(t => ({
  ...t,
  username: users.find(u => u.id === t.user_id)?.username
}))
```

JOIN 通过 `user_id = users.id` 这个「关联键」把两行拼成一行。

### 2. 三种 JOIN（核心记住前两个）

| JOIN 类型 | 结果 | 前端类比 |
|-----------|------|---------|
| **INNER JOIN** | 只保留两边都匹配的行 | `filter` + `map`（先丢对不上的，再拼接）|
| **LEFT JOIN** | 保留左表全部，右表匹配不上补 NULL | 直接 `map`，找不到给 `undefined`（不 filter）|
| **RIGHT JOIN** | 保留右表全部，左表补 NULL | LEFT JOIN 反着写，很少用 |

**LEFT JOIN 方向是相对的**：「左表」= `FROM` 后面那张表。`users LEFT JOIN todos`（保留所有用户）和 `todos LEFT JOIN users`（保留所有 todo）结果完全不同。

等价关系：`todos RIGHT JOIN users` ≡ `users LEFT JOIN todos`。

### 3. JOIN 语法三要素

```sql
SELECT t.title, u.username        -- ① 要哪些列（表别名点出来）
FROM todos t                      -- ② 从哪张表 + 别名
INNER JOIN users u ON t.user_id = u.id  -- ③ 连哪张表 + ON 关联条件
```

- **表别名**：`FROM todos t` 给表起短名，`t.title` 指 todos 的 title。类比变量重命名。
- **`ON` 是关联条件**：写「哪两列相等」，类比 `find(u => u.id === t.user_id)` 里的 `===`。
- **列要带表前缀**：两表都有 `id` 时，光写 `id` 报歧义错误，必须 `t.id` / `u.id`。

### 4. GROUP BY = 分组聚合（前端类比 `reduce`）

「每个用户有几条 todo」→ 按 username 分组，每组用 COUNT 数行数：

```sql
SELECT u.username, COUNT(t.id)
FROM users u
LEFT JOIN todos t ON t.user_id = u.id
GROUP BY u.id, u.username
```

- **分组键**：`GROUP BY` 后面写的列（每组的「标签」）。
- **统计值**：聚合函数把一组的多行「算成一个数」（`COUNT`/`SUM`/`AVG`/`MAX`/`MIN`）。
- **铁律**：`SELECT` / `ORDER BY` 里出现的列，要么在 `GROUP BY` 里，要么被聚合函数包着。否则报 `column "x" must appear in the GROUP BY clause`。

前端类比：`reduce` 按 key 分组后，每组只能输出「key」和「统计结果」，不能输出组内明细（比如 title 有多个，没法选）。

### 5. `COUNT(*)` vs `COUNT(列名)`

- `COUNT(*)`：数**行数**（NULL 也算）。
- `COUNT(列名)`：数该列**不是 NULL** 的行数。

LEFT JOIN 后没匹配上的行，右表列是 NULL。想数出「carol 有 0 条 todo」必须用 `COUNT(t.id)`，用 `COUNT(*)` 会错算成 1。

前端类比：`arr.length` vs `arr.filter(x => x !== null).length`。

### 6. `GROUP BY name` vs `GROUP BY id, name`

- **分组结果**：name 唯一时两者分组一样（一个 name 对应一个 id）；name 不唯一时，加 id 会分得更细。
- **列可用性**：分组后只有「分组键」里的列能在 SELECT/ORDER BY 用。想 `ORDER BY id` 就得把 id 加进 `GROUP BY`。练习里加 id **不是为了分组更细，而是为了解锁在 ORDER BY 里用 id 的资格**。

---

## 二、练习 ↔ 知识点映射

| 练习 | 函数 | 知识点 |
|------|------|--------|
| 1 | `join_todos_with_users` | INNER JOIN 基础（表别名 + ON）|
| 2 | `get_user_todos` | INNER JOIN + `WHERE` 参数化 + 列表推导取单列 |
| 3 | `get_todo_owner` | INNER JOIN 查单行 + `fetchone()` |
| 4 | `get_users_without_todos` | LEFT JOIN + `WHERE t.id IS NULL` 找右表缺失 |
| 5 | `count_todos_per_user` | LEFT JOIN + `GROUP BY` + `COUNT(t.id)` |
| 6 | `right_join_all_todos` | RIGHT JOIN（保留右表全部，孤儿补 NULL）|

---

## 三、练习纠错全记录

### 第 1 轮（练习 1、2）

**① `==` 写成 SQL 相等判断（练习 1、2 都犯）**
- 现象：`ON t.user_id == u.id`。
- 原因：把 SQL 当 JS/Python 写——SQL 里相等判断是单个 `=`，没有 `==`。
- 解决：`=`。
- ⚠️ 这是「SQL 当代码写」的老毛病（SQL CRUD 课就记过），这次又在 JOIN 的 ON 里犯。

**② `ORDER AESC` 拼错（练习 1）**
- 现象：`ORDER AESC u.id`。
- 原因：关键字 `ORDER BY` 少写 BY，`ASC` 拼成 `AESC`。
- 解决：`ORDER BY ... ASC`。

**③ `ORDER BY ASC t.id` 语序错（练习 1，第二轮）**
- 现象：`ORDER BY ASC t.id`。
- 原因：`ASC` 放错位置。
- 解决：列名在前方向在后 —— `ORDER BY t.id ASC`。

**④ 练习 2 漏 WHERE，参数 username 没用上**
- 现象：`SELECT t.title FROM todos t LEFT JOIN users u ON u.id = t.user_id`（无 WHERE，返回所有 todo）。
- 原因：题目要「查某个用户的 todo」，但完全没写 `WHERE` 过滤，函数参数 `username` 从头到尾没用到。
- 解决：加 `WHERE u.username = %s` + 参数化。

**⑤ 练习 2 返回格式错：`fetchall()` 直接 return**
- 现象：`return cur.fetchall()` 返回 `[('买牛奶',), ...]`（tuple 列表），题目要 `['买牛奶', ...]`（字符串列表）。
- 原因：`fetchall()` 每行是 tuple，即使只 SELECT 一列。
- 解决：`return [x[0] for x in cur.fetchall()]`（列表推导取每行第一列）。

**⑥ `fot` 拼错（练习 2）**
- 现象：`return [x[0] fot x in ...]`，报 `SyntaxError: invalid syntax`。
- 原因：列表推导关键字是 `for`，拼成 `fot`。
- 解决：`for`。

### 第 2 轮（练习 3、4）

**⑦ `usernae` 拼错（练习 3）**
- 现象：`u.usernae`。
- 原因：`username` 少了 `m`。
- 解决：`username`。

**⑧ 练习 4 三个问题**
- `u.usename` —— `username` 少了 `r`（又是这个高频词拼错）。
- `FROM user` —— 表名是 `users`（复数），写成了 `user`（单数），报 `relation "user" does not exist`。
- `return cur.fetchone()` —— 题目要「用户名列表」（list of str），应 `fetchall()` + 列表推导（同练习 2 的坑，没迁移过来）。

### 第 3 轮（练习 5，反复卡住的点）

**⑨ GROUP BY 只写 username，ORDER BY 却用 u.id**
- 现象：`GROUP BY u.username ORDER BY u.id`，报 `column "u.id" must appear in the GROUP BY clause`。
- 原因：`ORDER BY` 里的 `u.id` 不在分组键里（GROUP BY 规则：SELECT/ORDER BY 的列要么在分组键，要么被聚合）。
- 解决：`GROUP BY u.id, u.username`。

**⑩ 改错方向：把 u.id 加到 SELECT 而不是 GROUP BY**
- 现象：改成 `SELECT u.username, u.id, count(t.id) ... GROUP BY u.username`，仍报同样错误。
- 原因：误解了「把 u.id 补进 GROUP BY」，把 u.id 加到了 `SELECT`（还导致 SELECT 变成 3 列，返回格式也会错）。
- 解决：`SELECT` 保持 `u.username, COUNT(t.id)` 两列；改的是 `GROUP BY` 这一行 → `GROUP BY u.id, u.username`。
- ⚠️ 这是「GROUP BY 规则」理解不到位导致的连续两次卡壳，概念见知识点 4、6。

---

## 四、踩坑速查表

| 错误写法 | 报错 / 现象 | 正确写法 |
|---------|------------|---------|
| `ON t.user_id == u.id` | SQL 语法错误 | `ON t.user_id = u.id` |
| `ORDER AESC col` / `ORDER BY ASC col` | SQL 语法错误 | `ORDER BY col ASC` |
| `[x[0] fot x in ...]` | `SyntaxError: invalid syntax` | `[x[0] for x in ...]` |
| `return cur.fetchall()`（要字符串列表） | 返回 `[('x',), ...]` tuple 列表 | `[x[0] for x in cur.fetchall()]` |
| `usernae` / `usename` | `column ... does not exist` | `username` |
| `FROM user` | `relation "user" does not exist` | `FROM users` |
| `GROUP BY username ORDER BY id` | `column "id" must appear in the GROUP BY clause` | `GROUP BY id, username ORDER BY id` |
| `COUNT(*)`（LEFT JOIN 统计右表） | 没 todo 的用户数成 1 | `COUNT(t.id)` |

---

## 五、本次会话用户主动提问的概念点（= 需要反复巩固）

1. 「INNER JOIN 是不是求集合？」→ 匹配靠交集，但结果是「拼接 + 一对多展开」，不是单纯集合。
2. 「LEFT / RIGHT JOIN 没明白」→ 用 `filter + map` vs `map` 类比讲清。
3. 「GROUP BY 没明白」→ 用 `reduce` 分组类比讲清。
4. 「什么叫『在 GROUP BY 里面』」→ 术语没对齐，= `GROUP BY` 关键字后面那列。
5. 「统计值是什么」→ 聚合函数把一组多行算成的那个数。
6. 「`COUNT(*)` 和 `COUNT(列)` 区别」→ NULL 算不算数。
7. 「`GROUP BY name` vs `GROUP BY id, name` 区别」→ 分组结果 + 列可用性两个层面。
