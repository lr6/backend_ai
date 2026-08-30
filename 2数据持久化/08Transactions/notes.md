# 学习项 8 · Transactions — 事务与隔离级别

> 完成日期：2026-08-30 ｜ 7 个练习全部通过 🎉
> 练习库：`transaction_practice_db`（新建，未动旧的 `todo_orm_db` / `alembic_practice_db`）

---

## 一、知识点讲解

### 1. 事务（Transaction）是什么

**事务 = 一组 SQL 的「打包执行」**：
- `COMMIT` → 全部生效（落地）
- `ROLLBACK` → 全部作废（丢弃）

**前端类比**：就像编辑文件后点「保存」（COMMIT）才写盘；「撤销到上次保存」（ROLLBACK）所有改动一起没了。

psycopg 里默认 `autocommit=False`：**执行第一条 SQL 就自动开启一个事务**，之后所有 SQL 都在这个事务里，直到 `conn.commit()` 或 `conn.rollback()`。

### 2. ACID 四要素

| 字母 | 含义 | 前端类比 |
|------|------|---------|
| **A**tomicity 原子性 | 一组操作要么全成、要么全败，不能只做一半 | 转账 = 扣钱 + 加钱必须一起发生 |
| **C**onsistency 一致性 | 事务前后数据必须合法（约束不破） | 扣 30 块，对方就必须多 30 块，账要平 |
| **I**solation 隔离性 | 多个事务并发互不干扰 | 两人同时编辑共享文档，改动要能区分 |
| **D**urability 持久性 | COMMIT 后数据永久保存，断电不丢 | 保存后关浏览器，数据还在 |

### 3. 并发三大问题

| 问题 | 一句话 | 场景 |
|------|--------|------|
| **脏读** Dirty Read | 读到**别人还没提交**的数据 | A 改了没提交，B 读到 0；A 回滚后 B 读了个假数据 |
| **不可重复读** Non-repeatable Read | 同一事务读同一行两次，**两次结果不同** | 事务里读余额 100，中途别人改成 50 提交，再读变 50 |
| **幻读** Phantom Read | 同一事务查询两次，**行数变了** | 事务里数出 2 行，中途别人插入 1 行提交，再数变 3 |

> ⚠️ 关键区分：**自己连接读自己未提交的修改，当然看得到**；脏读特指「别的连接」读到未提交数据。验证隔离性必须用另一个连接去读。

### 4. 隔离级别

PostgreSQL 用隔离级别控制「我这个事务能看到别人已提交/未提交的什么」。**级别越高越防问题，但并发性能越差**。

PG 实际支持的级别（**不支持 READ UNCOMMITTED**，按 READ COMMITTED 处理）：

| 隔离级别 | 脏读 | 不可重复读 | 幻读 | 说明 |
|---------|:---:|:---:|:---:|------|
| READ COMMITTED（PG 默认）| ✅ | ❌ | ❌ | 只看到已提交的数据 |
| REPEATABLE READ | ✅ | ✅ | ✅（PG 比标准强）| **快照隔离**：事务开始时拍快照，全程读快照 |
| SERIALIZABLE | ✅ | ✅ | ✅ | 最强，像所有事务排队执行 |

**前端类比**：REPEATABLE READ 快照隔离就像 Git 的 commit——事务开始那一刻拍了个快照，之后别人怎么改，你读到的都是自己快照里的版本。

开启指定隔离级别：`BEGIN ISOLATION LEVEL REPEATABLE READ`（字符串拼接时**注意空格**）。

### 5. 行锁 `SELECT ... FOR UPDATE`

「先读、再改、再写」中间可能被别的连接插一脚。**悲观锁**方案：`SELECT ... FOR UPDATE` 锁住这一行。

**关键：锁会一直持有到事务结束（commit 或 rollback）**，不是锁一下就完。拿锁的代码通常和 commit/rollback 分开在不同地方（拿锁处只锁不提交，由调用方统一提交/回滚释放锁）。

### 6. SQLAlchemy Session 本质就是事务

学习项 6 用的 `session.commit()` / `session.rollback()`，底层就是一个数据库事务。Session 打开 = 事务开始，commit/rollback = 结束。ORM 对象改属性后 commit 会自动生成 UPDATE——SQL 被藏进了 ORM 层。

---

## 二、练习 ↔ 知识点映射

| 练习 | 考点 | 关键代码要点 |
|------|------|------------|
| 1 `transfer` | 原子性 + COMMIT | 两条 UPDATE 在同一个事务里，commit 后才生效 |
| 2 `transfer_with_check` | 原子性 + ROLLBACK | 余额不足时 `raise` + `conn.rollback()` |
| 3 `dirty_read_check` | 隔离性、无脏读 | `conn_a` 改不提交，`conn_b` 读 → 读到旧值 100 |
| 4 `read_twice` | 不可重复读 + 隔离级别 | BEGIN + 读两次，中间 conn_b 改并 commit；(100,50) vs (100,100) |
| 5 `count_twice` | 幻读 + 隔离级别 | BEGIN + 数两次，中间 conn_b 插入并 commit；(2,3) vs (2,2) |
| 6 `lock_balance` | 行锁 FOR UPDATE | `SELECT ... FOR UPDATE`，**只锁不提交** |
| 7 `sa_transfer` | SQLAlchemy 事务 | `session.get` → 改属性 → `session.commit()` / rollback |

---

## 三、练习纠错全记录

### 练习 1：一次通过 ✅
- 小问题：`(amount, from_id,)` 尾部多余逗号，不影响正确性。

### 练习 2：`transfer_with_check`（改 2 次）
**问题 2-1：`return ValueError('余额不足')` 不抛异常**
- 现象：测试报「余额不足时应抛 ValueError」，且代码不报错
- 原因：`return` 只是把异常对象当普通值返回，`except ValueError:` 捕捉不到
- 知识点：`return`（交还调用方）vs `raise`（报告错误）——**学习项 2 踩过同一个坑**
- 解决：改成 `raise ValueError('余额不足')`

**问题 2-2：`conn.execcute` 拼写错误**
- 现象：`AttributeError: 'Connection' object has no attribute 'execcute'`
- 原因：`execcute` 多了个 c，psycopg 的 Connection 没有这个方法
- 知识点：SQL 字符串和属性名都是手敲的，拼错没有「智能提示」
- 解决：改成 `conn.execute`

**问题 2-3：返回值类型不对**
- 现象：`return f"from {cur_balance}, to {cur2_balance}"` 返回字符串
- 原因：测试期望 tuple `(70, 80)`，字符串永远不相等
- 解决：返回 `(cur_balance, cur2_balance)`

### 练习 3：`dirty_read_check`（改 1 次）
**问题：变量名 + 缺引号 + 读的视角错**
- 现象：第一行 `conn.execute` 就 `NameError`（函数参数是 conn_a/conn_b，没有 conn）
- 原因：
  1. 用 `conn` 而非 `conn_a`（改）/`conn_b`（读）
  2. `WHERE name = alice` 没加引号，`alice` 被当成列名 → SQL 语法错误
  3. **核心逻辑错**：在同一个连接上读自己未提交的修改（看到 0），这不是脏读；脏读要**另一个连接**读到未提交数据
- 知识点：脏读的定义、README COMMITTED 只看已提交数据
- 解决：`conn_a` 改不提交 → `conn_b` 读 → `conn_a` 回滚 → 返回 conn_b 读到的 100

### 练习 4：`read_twice`（改 2 次）
**问题 4-1：字符串拼接缺空格**
- 现象：`'BEGIN ISOLATION LEVEL' + isolation` 拼出 `LEVELREAD COMMITTED` → SQL 语法错误
- 原因：字符串拼接不会自动加空格
- 解决：`'BEGIN ISOLATION LEVEL ' + isolation`（末尾留空格）

**问题 4-2：`'alice` 引号没闭合（3 处）**
- 现象：`SELECT ... WHERE name = 'alice"` 结尾缺 `'`
- 解决：`'alice'` 一前一后两个引号

**问题 4-3：conn_b 改完没 COMMIT**
- 现象：READ COMMITTED 下第二次读还是 100，测试期望 (100,50)
- 原因：conn_b 不 commit，修改就是「未提交」，conn_a 读不到
- 解决：`conn_b.execute(UPDATE)` 后补 `conn_b.commit()`

**问题 4-4（重点坑）：中文输入法弯引号 `‘` `’`**
- 现象：`SyntaxError: unterminated quoted string at or near "'alice‘"`，报错光标指向引号位置
- 原因：打 `'alice'` 时结尾 `'` 被中文输入法（全角模式）自动转换成弯引号 `‘`/`’`（U+2018/2019）。**PostgreSQL 只认直引号 `'`（U+0027）作为字符串边界**，弯引号只是普通字符 → 字符串永远没闭合
- 解决：把 `‘` `’` 全部换成英文直引号 `'`

### 练习 5：`count_twice`（改 1 次）
**问题 5-1：表名拼错 `account` → `accounts`（2 处）**
- 现象：`relation "account" does not exist`
- 解决：`SELECT COUNT(*) FROM accounts`

**问题 5-2：VALUES 里逗号被引号包住**
- 现象：`VALUES ('bobo, 2000')` 报 `INSERT has more target columns than expressions`
- 原因：逗号在字符串里面 → 整个 `bobo, 2000` 成一个值，2 列对 1 个值
- 知识点：**逗号在引号里 = 它是值的一部分；分隔两个值，逗号必须在引号外**
- 解决：`VALUES ('bobo', 2000)`

### 练习 6：`lock_balance`（改 1 次）
**问题：函数内 `conn.commit()` 提前释放行锁**
- 现象：测试报「行没被锁住！worker 不应在 conn_a 提交前完成 UPDATE」
- 原因：`SELECT ... FOR UPDATE` 的锁持有到事务结束；函数里 commit 把事务结束了，锁立刻释放
- 知识点：FOR UPDATE 锁的释放时机
- 解决：删掉 `conn.commit()`，只锁不提交

### 练习 7：`sa_transfer`（一次通过 ✅）
- 小遗憾：余额不足时没写 `session.rollback()`（概念上应补，但先查后改、未改任何数据，测试不受影响）

---

## 四、踩坑速查表

| 错误写法 | 报错 | 正确写法 |
|---------|------|---------|
| `return ValueError("余额不足")` | 测试报「应抛 ValueError」 | `raise ValueError("余额不足")` |
| `conn.execcute(...)` | `AttributeError: no attribute 'execcute'` | `conn.execute(...)` |
| `WHERE name = alice` | SQL 语法错误（alice 当列名）| `WHERE name = 'alice'` |
| `'BEGIN ISOLATION LEVEL' + x` | `LEVELREAD COMMITTED` 语法错误 | `'BEGIN ISOLATION LEVEL ' + x`（留空格）|
| `WHERE name = 'alice‘`（弯引号）| `unterminated quoted string` | `WHERE name = 'alice'`（直引号）|
| `FROM account` | `relation "account" does not exist` | `FROM accounts` |
| `VALUES ('bobo, 2000')` | `more target columns than expressions` | `VALUES ('bobo', 2000)` |
| FOR UPDATE 后立即 commit | 锁提前释放，别人不被阻塞 | 只锁不提交，等统一 commit/rollback |
| 自己连接读自己未提交的改动 | 读到 0，误以为「有脏读」 | 用**另一个连接**读才是隔离性视角 |
