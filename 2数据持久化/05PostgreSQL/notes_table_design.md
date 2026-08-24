# 5 PostgreSQL — 表设计（约束、主键、外键）笔记

> 学习日期：2026-08-24
> 状态：学习项 5 进行中（本笔记覆盖「表设计」部分；JOIN、索引待学）

---

## 一、知识点讲解

### 1. 建表 = 定义「数据长什么样」+「什么数据合法」

建表时给每列定**数据类型** + 加**约束**，两者就像 TS 的 `interface` + 表单校验。

### 2. 数据类型（前端类比：TS interface）

| PostgreSQL 类型 | 含义 | TS 类比 |
|----------------|------|---------|
| `INTEGER` | 整数 | `number` |
| `TEXT` | 文本（不限长） | `string` |
| `BOOLEAN` | 布尔 | `boolean` |
| `SERIAL` | 自增整数（自动 +1） | 无（类似自动生成的唯一 id） |
| `NUMERIC(10,2)` | 精确小数（共10位，2位小数） | `number` |
| `TIMESTAMP` | 日期时间 | `Date` |

### 3. 约束 = 数据库帮你做「表单校验」

| 约束 | 作用 | 前端类比 |
|------|------|---------|
| `NOT NULL` | 不能为空 | `required` 必填 |
| `UNIQUE` | 值不能重复 | 注册时「用户名已存在」 |
| `CHECK (条件)` | 自定义校验 | 年龄范围、密码长度校验 |
| `DEFAULT 值` | 默认值 | 表单初始值 |

约束写在列定义后面，同一列可叠多个（空格分隔，不是逗号）：
```sql
username TEXT NOT NULL UNIQUE
age      INTEGER CHECK (age >= 0 AND age <= 150)
```

### 4. 主键 vs 外键

- **主键 PRIMARY KEY**：唯一标识一行，每张表都要有。本质是 `NOT NULL + UNIQUE`。
- **外键 FOREIGN KEY**：引用**另一张表的主键**，建立「关系」。数据库**强制检查**外键值必须存在，不能「悬空」。

前端类比：
```js
const user = { id: 1, username: 'alice' }        // id 是主键
const todo = { id: 1, title: '买牛奶', userId: 1 } // userId 是外键 → 指向 user.id
```

### 5. 一对多关系

```sql
CREATE TABLE users (
    id       SERIAL PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    email    TEXT NOT NULL UNIQUE,
    age      INTEGER CHECK (age >= 0 AND age <= 150)
);

CREATE TABLE todos (
    id      SERIAL PRIMARY KEY,
    title   TEXT NOT NULL,
    user_id INTEGER NOT NULL REFERENCES users(id)   -- 外键
);
```

一个用户有多个 todo →「一对多」，`todos.user_id` 指向 `users.id`。这是阶段项目（Todo + 用户表）的雏形。

### 6. 附加：SERIAL 自增序列 & TRUNCATE vs DELETE

- **SERIAL** 底层是「序列（sequence）」+ `nextval`。**即使 INSERT 失败，序列也会被消耗**（`nextval` 被调用过）。
- `DELETE FROM 表` —— 删数据，但**不重置序列**（下次 id 接着涨）。
- `TRUNCATE 表 RESTART IDENTITY` —— 清空表**并重置序列**（id 从 1 重新开始）。

---

## 二、练习 ↔ 知识点映射

| 练习 | 函数 | 知识点 |
|------|------|--------|
| 1 | `create_users_table` | `CREATE TABLE` + `NOT NULL`/`UNIQUE`/`CHECK` 约束 |
| 2 | `create_todos_table` | 外键 `REFERENCES users(id)` |
| 3 | `insert_user` | `INSERT` + 多个 `%s` 参数化 + `RETURNING id` |
| 4 | `insert_todo` | `INSERT` + 外键列值 |
| 5 | `get_user_by_username` | `SELECT WHERE`（UNIQUE 列）+ `fetchone()` 整行 |
| 6 | `insert_duplicate_username` | UNIQUE 约束拦截 + `try/except` |

---

## 三、练习纠错全记录

### 第 1 轮：4 个错误（类型齐全）

**① `INTERGE` 拼写错误（练习 1、2 各一遍）**
- 现象：`age INTERGE CHECK (...)`、`user_id INTERGE ...`
- 原因：把 `INTEGER` 拼成了 `INTERGE`（多了一个 R）——**同一个错写了两遍**，说明拼写记错了。
- 解决：`INTEGER`（`INTE` + `GER`）。

**② 练习 3 缺 `RETURNING id`**
- 现象：`INSERT INTO users ... VALUES (%s,%s,%s)`（无 RETURNING），`fetchone()[0]` 报 `TypeError`（`fetchone()` 返回 `None`）。
- 原因：`INSERT` 默认不返回任何行，要 `RETURNING id` 才能拿到自增 id。
- 解决：`... VALUES (%s,%s,%s) RETURNING id`。

**③ 练习 5 缺 `WHERE`**
- 现象：`SELECT * FROM users username = %s`。
- 原因：条件查询少了 `WHERE` 关键字。
- 解决：`SELECT * FROM users WHERE username = %s`。类比 JS 的 `filter` 就是 `WHERE`。

**④ 练习 5 `fetchone()[0]` 应改为 `fetchone()`**
- 现象：`SELECT *` 却返回 `fetchone()[0]`（只取第一个字段 id）。
- 原因：混淆「取单个字段」和「取整行」。
- 解决：一列（如 `RETURNING id`）用 `fetchone()[0]`；整行（`SELECT *`）用 `fetchone()`。

### 第 2 轮：练习 5 还剩 2 处

**⑤ `sername` 拼写错误**
- 现象：`WHERE sername = %s`。
- 原因：`username` 少了开头的 `u`。
- 解决：`username`。

**⑥ `(username)` 不是元组（缺逗号）**
- 现象：参数化传 `(username)`。
- 原因：`(x)` 只是「分组」，等于 `x` 本身；`(x,)` 才是元组。括号是「分组」，**逗号才是「元组」的标志**。
- 解决：`(username,)`。
- ⚠️ 这个点 SQL CRUD 课练习 2 写对过（`(title,)`），这里又写错——反复出现的点，说明还没形成稳定认知，务必记牢。

### 第 3 轮：测试代码 bug（SERIAL 序列被失败 INSERT 消耗）

- 现象：练习 3 报「期望 id=1 实际 3」、练习 4 报外键「user_id=1 不存在」、练习 4 报「期望 id=1 实际 2」。
- 原因：测试里用「失败 INSERT」验证约束，这些失败 INSERT 会消耗 SERIAL 序列；`DELETE FROM users` 又不重置序列。
- 解决：测试里改用 `TRUNCATE ... RESTART IDENTITY` 重置序列。
- **这不是用户代码错，是测试框架 bug**，但引出了一个真知识点（见知识点 6）。

---

## 四、踩坑速查表

| 错误写法 | 报错 / 现象 | 正确写法 |
|---------|------------|---------|
| `INTERGE` | 建表语法错误 | `INTEGER` |
| `INSERT ... VALUES (...)` 缺 `RETURNING id` | `fetchone()` 返回 `None`，`None[0]` 报 `TypeError` | `... RETURNING id` |
| `SELECT * FROM t col = %s`（缺 WHERE） | SQL 语法错误 | `SELECT * FROM t WHERE col = %s` |
| `SELECT *` 后 `return cur.fetchone()[0]` | 只返回第一个字段 | `return cur.fetchone()` |
| `sername` | `column "sername" does not exist` | `username` |
| `(x)` 没逗号 | 不是元组，参数化报错 | `(x,)` |
| 失败 INSERT 后用 `DELETE` 清空 | id 不连续（序列没重置） | `TRUNCATE ... RESTART IDENTITY` |
