# 学习项 24 · Database Indexes — B-Tree、EXPLAIN ANALYZE

> 学习日期：2026-11-28
> 练习库：`index_practice_db`，表 `big_todos` 100 万行
> 练习文件：`practice.py`（8 个练习，全部通过，连跑两次确认可重复）

---

## 一、知识点讲解

### 1. 索引是什么

**没索引**：`Seq Scan`（顺序扫描），逐行比对条件，100 万行 = 100 万次比对。

**有索引**：不扫表，在一份**按列值排好序**的结构里定位。

结构叫 **B-Tree**，特点不是「聪明」而是「矮胖」：

- 每个节点挂很多分支（不是二叉树）
- 100 万行只有 3~4 层
- 每往下一层 = 读一次磁盘页
- 定位一条 ≈ 3~4 次读，而不是 100 万次

**索引里存什么**：不是整行，而是「排好序的列值 + 行的位置（`ctid`）」。查询是两步：

1. 在索引里找到目标条目 → 拿到一批 `ctid`
2. 按 `ctid` **回表**取出完整行（heap fetch）

**自动索引**：主键和 UNIQUE 约束会**自动**建索引。所以 `WHERE id = ?` 一直有索引兜着，只是看不见。

**代价**：

- 写放大：每次 INSERT/UPDATE/DELETE，每个索引都要维护有序结构；UPDATE 改索引列 = 删旧条目 + 插新条目
- 空间：索引独立存储
- 优化器负担：索引越多，规划时权衡的组合越多

> 结论：只给「经常出现在 WHERE / JOIN / ORDER BY 里、且区分度高」的列建索引。

---

### 2. EXPLAIN vs EXPLAIN ANALYZE

| 命令 | 做什么 |
|------|--------|
| `EXPLAIN` | 只让数据库说它**打算**怎么执行，不真跑 |
| `EXPLAIN ANALYZE` | **真跑一遍**，附上真实耗时和行数 |
| `EXPLAIN (ANALYZE, BUFFERS)` | 再加缓存/磁盘读页数 |
| `EXPLAIN (ANALYZE, FORMAT TEXT)` | 文本格式（默认也是 TEXT，写出来更明确） |

计划是一棵**树**：每行一个节点，缩进表示父子，**父节点耗时包含子节点**。

---

### 3. 关键指标（读计划的全部依据）

#### 3.1 节点类型

| 类别 | 节点 | 含义 |
|------|------|------|
| 扫描 | `Seq Scan` / `Parallel Seq Scan` | 全表扫，没走索引 |
| | `Index Scan` | 走索引 + 回表 |
| | `Index Only Scan` | 只读索引，不回表（最快） |
| | `Bitmap Index Scan` + `Bitmap Heap Scan` | 先攒一批位置，再批量回表 |
| 连接 | `Nested Loop` | 外层每行去内层查一次（外层小） |
| | `Hash Join` | 建哈希表再探测（两边都大、无序） |
| | `Merge Join` | 两边都按连接键有序时归并 |
| 其他 | `Sort` / `Limit` / `Aggregate` / `Gather` | 排序 / 取前 N / 聚合 / 收集并行结果 |

#### 3.2 `cost=启动..总`

```
cost=5.20..10214.82
```

- 单位是内部「代价分」：默认顺序读一页 1 分、随机读一页 4 分、处理一行 CPU 0.01 分
- **只能比较同一查询的不同计划**，不能当毫秒看
- 启动 = 返回第一行之前；总 = 全部返回完
- 有 `LIMIT` 时启动代价更重要

#### 3.3 `rows=` 估算 vs `actual rows=` 实际（最该盯）

```
rows=3306 ... (actual time=0.107..1.594 rows=500 loops=1)
```

- 前面 `rows=` 是优化器**根据统计信息猜的**
- `actual rows=` 是**实测的**
- 差 10 倍以上要警惕：统计信息过期 / 数据倾斜 / 条件太复杂

**实测案例**：`users_demo` 新建表没跑 `ANALYZE`，`WHERE id <= 5` 估算 **33**、实际 **5** —— 没有统计信息时，范围条件按默认「命中 1/3」猜（100 × 1/3 ≈ 33）。误差还往上传：`Nested Loop` 估算 3306、实际 500。

跑 `ANALYZE users_demo` 后：估算变 **401**（实际 500），计划也从 `Nested Loop` 换成了 `Merge Join` —— 统计信息直接影响「选哪个计划」。

#### 3.4 `width=`

平均每行字节数。影响排序 / 哈希表的内存占用和 IO 量。一般不是问题指标，但「width 大 + 行数多」要小心。

#### 3.5 `actual time=启动..总`

```
actual time=0.051..0.265
```

- 单位毫秒，**每次循环的平均值**
- 第一个数：返回第一行耗时（启动）
- 第二个数：全部行返回完耗时
- `LIMIT` 场景看启动时间：索引有序 → 立刻返回前 N 行，不用等排序

#### 3.6 `loops=`（最容易误读）

```
Bitmap Heap Scan ... (actual time=0.051..0.265 rows=100 loops=5)
```

- 节点被执行了 5 次（外层每行进来查一次）
- `actual rows=100` 是**每次循环的平均值**，不是总数
- **总行数 = rows × loops = 100 × 5 = 500**
- **总耗时 ≈ 0.265ms × 5 = 1.325ms**
- 只有 `loops > 1` 的节点才需要乘；最外层 `loops=1` 的 `actual rows` 已经是最终结果

**self time 算法**：某节点自己花的 = 自己的总耗时 − 子节点总耗时。

```
Nested Loop       1.594ms
- 外层 Seq Scan   0.034ms
- 内层 Bitmap     1.325ms
= 自身开销        0.235ms
```

优化时找 `self time × loops` 最大的节点，而不是最外层数字。

#### 3.7 `Index Cond` / `Filter` / `Rows Removed by Filter`

- **`Index Cond`**：条件下推到索引，只取匹配条目 —— 理想
- **`Filter`**：行取出来后才筛，不匹配扔掉；`Rows Removed by Filter` = 白取的数量
- 大表上 `Rows Removed by Filter` 巨大 = 信号：条件没索引可用，或选择性太差
- `Bitmap Heap Scan` 的 **`Recheck Cond`**：位图可能按「页」记录（lossy），回表后再校验，属正常机制

#### 3.8 `Buffers`（需要 `BUFFERS` 选项）

```
Buffers: shared hit=515 read=1
```

- `hit`：命中共享缓存；`read`：从磁盘读的页数
- 命中率 = hit ÷ (hit + read)
- **冷缓存**第一遍慢、第二遍快，是缓存效应；对比性能前先预热

#### 3.9 `Planning Time` vs `Execution Time`

- `Planning Time`：生成计划（不含执行）
- `Execution Time`：执行（不含规划）
- 复杂 JOIN / 分区表规划可能比执行还久；prepared statement 可省重复规划

#### 3.10 实战四步

1. 找 `self time × loops` 最大的节点
2. 比 `rows=` 估算 vs 实际，差 10 倍以上 → `ANALYZE 表`
3. 看 `Rows Removed by Filter`，巨大 → 索引缺失或选择性差
4. 看 `loops` 与 `Buffers`：loops 大 = 重复执行；read 多 = 冷缓存 / 数据太大

#### 3.11 红旗速查

| 现象 | 可能原因 | 处理 |
|------|---------|------|
| 大表 `Seq Scan` + 高选择性条件 | 缺索引 | 建索引 |
| 估算 vs 实际差 10 倍以上 | 统计信息过期 | `ANALYZE 表` |
| `Rows Removed by Filter` 巨大 | 索引失效 / 选择性低 | 改查询 / 换索引 |
| `loops` 大 + 内层慢 | 嵌套循环放大（N+1） | 批量查询 / 换连接方式 |
| `Sort Method: external merge Disk` | 排序内存不够 | 加索引 / 调 `work_mem` |
| `read` 远大于 `hit` | 冷缓存 / 数据太大 | 预热 / 加内存 |
| `Planning Time` 占比高 | 查询太复杂 | 简化 / prepared statement |

---

### 4. 选择性（selectivity）

`选择性 = 命中行数 ÷ 总行数`。索引擅长**跳过大部分行**，不是「快」本身。

实测（`done` 上建了索引）：

| 查询 | 命中 | 计划 | 耗时 |
|------|------|------|------|
| `WHERE done = true` | 99 万（99%） | `Seq Scan` | 54.9ms |
| `WHERE done = false` | 1 万（1%） | `Index Scan` | 9.1ms |

99% 命中走索引 = 99 万次**随机回表**，比顺序扫全表更贵。优化器算完账会放弃索引。

> 索引是「少数派筛选器」。低选择性列（布尔、状态）单独建索引基本没用。

---

### 5. 复合索引与最左前缀

`(user_id, done)` 的排序规则：先按 `user_id` 排，`user_id` 相同的再按 `done` 排。

- `WHERE user_id = 42` → 能定位连续区域 ✅
- `WHERE done = false` → 该值散落在所有 user_id 分组里 ❌
- `WHERE user_id = 42 AND done = false` → 两列都能用（`Index Cond` 两个条件）✅

类比：电话簿按「姓、名」排序 —— 找「所有姓张的」可以，找「所有名字叫伟的」不行。

**设计规则**：等值条件列在前，范围/排序列在后。

---

### 6. 索引失效场景

| 写法 | 为什么失效 | 解法 |
|------|-----------|------|
| `WHERE lower(title) = 'x'` | 索引存原值，函数结果是另一套值 | 表达式索引 `ON t(lower(title))` |
| `WHERE title LIKE '%abc'` | 前导通配符，索引从左到右才能用 | 改前缀匹配 / 全文索引 / trigram |
| 字符串列传数字（类型不匹配） | 隐式转换 = 套函数 | 统一类型 |
| 低选择性列单独建 | 优化器不用 | 复合索引 / 部分索引 |

---

### 7. ORDER BY + LIMIT 依赖索引

`SELECT * FROM big_todos ORDER BY created_at LIMIT 10`：

| 状态 | 计划 | 耗时 |
|------|------|------|
| 无索引 | 100 万行排序（top-N heapsort，并行） | 27.7ms |
| 有索引 | 索引天然有序，走 10 条就停 | 0.07ms |

分页查询 `ORDER BY ... LIMIT` 必须配索引，否则每翻一页都把全表排一遍。

---

### 8. 什么时候**不**该建索引

| 场景 | 原因 |
|------|------|
| 表只有几千行 | 全表扫本来就快 |
| 写多读少（日志、事件表） | 每个索引都要维护，写变慢 |
| 低选择性列单独建 | 99% 命中，优化器不用 |
| 分析型全表聚合 | `SUM/COUNT` 扫全表，索引帮不上 |
| 复合索引已覆盖 | `(user_id, created_at)` 已能服务单列 `user_id` |

---

### 9. 工程落地（全栈角色）

- 索引是 **schema 的一部分**，要进代码和迁移：

```python
# SQLAlchemy 模型
__table_args__ = (
    Index("idx_todos_user_created", "user_id", "created_at"),
)
```

```python
# Alembic 迁移
op.create_index("idx_todos_user_created", "todos", ["user_id", "created_at"])
```

- **外键列不会自动建索引**（PG 只自动给 PK / UNIQUE 建）。`todos.user_id` 要手动加
- 大表上线用 `CREATE INDEX CONCURRENTLY`（不锁表建索引）
- 部分索引：`CREATE INDEX ... ON todos(created_at) WHERE status = 'failed'`，只索引需要的行

---

## 二、练习 ↔ 知识点映射

| 练习 | 函数 | 对应知识点 |
|------|------|-----------|
| 1 | `plan_text` | EXPLAIN ANALYZE 输出结构、cursor / fetchall |
| 2 | `plan_rows` | 估算 rows vs 实际 rows、正则解析 |
| 3 | `uses_index` | 节点类型判定（Seq Scan / Index Scan / Index Only Scan） |
| 4 | `index_on_user_id` | 建索引前后对比、回表、ANALYZE |
| 5 | `selectivity` | 选择性、随机回表 vs 顺序扫 |
| 6 | `leftmost_prefix` | 复合索引最左前缀 |
| 7 | `function_kills_index` | 函数包裹列导致索引失效 |
| 8 | `order_by_limit` | ORDER BY + LIMIT 依赖有序索引 |

---

## 三、练习纠错全记录

### 3.1 探底（两题）

- Q1「索引怎么找」：答「user_id 不是主键，可能一行一行对比」—— 对了一半，描述了**没索引**时的 Seq Scan，不知道有索引时的 B-Tree 寻址
- Q2「读执行计划」：答「读不懂，不知道」→ 直接讲

### 3.2 练习 1：`FORM` typo

现象：测试报

```
SyntaxError: unrecognized EXPLAIN option "form"
```

原因：写成 `EXPLAIN (ANALYZE, FORM TEXT)`，少 `AT`。
对应知识点：EXPLAIN 选项拼写。
解决：改为 `FORMAT TEXT`。

顺带验证：`)SELECT` 没有空格**也能解析**（SQL 不靠空格断句），但加上空格更可读。

### 3.3 练习 1 讲解时「还是不懂」

拆解数据流后才通过：

```
cursor → [ (str,), (str,), ... ] → [ str, str, ... ] → "str\nstr\n..."
         fetchall()               row[0]            "\n".join()
```

关键点：`fetchall()` 返回的是「只有一个字符串的 tuple」的列表，不能直接 `join(rows)`。

### 3.4 loops 误解（核心错题）

计划：

```
Nested Loop  ... rows=500 loops=1
  -> Seq Scan users_demo ... rows=5 loops=1
  -> Bitmap Heap Scan ... rows=100 loops=5
```

问「join 实际返回多少行、内层总耗时多少」，用户答 **2500**。

正确：**500 行**，内层约 **1.325ms**。

- 2500 的来源：把已经汇总的 500 又乘了 loops=5
- 规则：**只有 `loops > 1` 的节点才乘**；最外层 `loops=1`，`actual rows` 就是最终结果
- 内层每次 100 行 × 5 次 = 500 行；耗时 0.265ms × 5 ≈ 1.3ms
- self time = 1.594 − 0.034 − 1.325 ≈ 0.235ms

### 3.5 应用题：列表接口的索引设计（错题）

需求：`GET /todos?done=false`，按 `created_at` 倒序，每页 20 条（每个用户只看自己的）。

用户答案：「`done=false` 建部分索引，`created_at` 也建索引」。

**问题**：

1. 漏了 `user_id` —— 列表是按当前用户过滤的，没有 user_id，索引会扫描所有用户的待办
2. 两条单列索引**无法组合出排序** —— B-Tree 只能利用一条索引的有序性；两条单列索引最多做 bitmap AND 过滤，之后还得排序

**正确设计**（一条部分复合索引）：

```sql
CREATE INDEX idx_todos_user_created_pending
ON todos (user_id, created_at DESC)
WHERE done = false;
```

规则：

- **等值条件列在前**（`user_id`），**排序列在后**（`created_at`）
- 固定不变的过滤条件（`done = false`）放进 `WHERE` 子句做部分索引，索引更小
- 如果还要「全部待办」列表：用 `(user_id, done, created_at)`，或再建一条不带 WHERE 的 `(user_id, created_at)`

### 3.6 应用题：单条 / 删除用户（答对）

- 单条 `WHERE id = ? AND user_id = ?`：主键索引已经够用（先按 id 定位一行，再校验 user_id）。user_id 索引不是为它服务的
- 删除用户：需要 `todos(user_id)` 索引，否则 PG 要扫全表 todos 找子行 —— 用户项目里这个索引**目前缺失**

**应用题的最终答案**：

| 路径 | 查询 | 现有索引 | 需要补 |
|------|------|---------|--------|
| 列表 | `user_id=? AND done=false ORDER BY created_at DESC LIMIT 20` | 无 | 部分复合 `(user_id, created_at) WHERE done=false` |
| 单条 | `id=? AND user_id=?` | `todos_pkey` | 够用 |
| 删用户 | `users.id → todos.user_id` | 无 | `todos(user_id)` |

### 3.7 「这节知识点感觉没应用」的讨论

用户质疑这章的应用价值。核心回应：

- 现在 `eng_todo_db` 是 **0 行数据**，所以感觉不到 —— 数据量小时全表扫和索引一样快
- 真实应用点：分页列表索引、外键列索引（删用户）、UNIQUE 查询、后台状态扫描（部分索引）、线上慢接口排查
- 反面同样重要：小表、写多读少、低选择性列**不该**建索引
- 索引要写进 Alembic 迁移，是全栈角色的 schema 职责

---

## 四、实测数据汇总（index_practice_db）

`big_todos`：100 万行，`user_id` 1..10000（每人 100 行），`done` 99 万 true / 1 万 false。

| 场景 | 无索引 / 前 | 有索引 / 后 |
|------|------------|------------|
| `WHERE user_id = 42` | 42.6ms（Parallel Seq Scan） | 0.15ms（Bitmap Heap Scan） |
| `WHERE done = true`（99%） | 54.9ms（Seq Scan） | 优化器仍选 Seq Scan |
| `WHERE done = false`（1%） | — | 9.1ms（Index Scan） |
| `ORDER BY created_at LIMIT 10` | 27.7ms（Sort） | 0.07ms（Index Scan） |
| `WHERE user_id=42` 估算 vs 实际 | — | 99 vs 100 |
| `users_demo` 无统计信息 | 估算 33 / 实际 5 | ANALYZE 后估算 401 / 实际 500 |

---

## 五、踩坑速查表

| 错误写法 / 理解 | 现象 | 正确写法 / 理解 |
|----------------|------|----------------|
| `EXPLAIN (ANALYZE, FORM TEXT)` | `unrecognized EXPLAIN option "form"` | `FORMAT TEXT` |
| `"\n".join(rows)` | TypeError | 先 `row[0]` 再 join |
| `loops=5` 时把 top rows 再乘 5 | 2500 ≠ 500 | 只有 loops>1 的节点才乘 |
| 部分索引 + 单列 created_at 索引 | 无法提供组合排序 | 一条部分复合 `(user_id, created_at) WHERE done=false` |
| 给 `done` 建普通索引 | 99% 命中时不走 | 部分索引 / 复合索引 / 不建 |
| `WHERE lower(title)=...` | Seq Scan | 表达式索引 `ON t(lower(title))` |
| `WHERE title LIKE '%x'` | Seq Scan | 前缀匹配 / trigram / 全文索引 |
| 只看最外层耗时 | 找不到瓶颈 | 算 self time × loops |
| 建索引后不 `ANALYZE` | 优化器可能不选 | 建完跑 `ANALYZE 表` |
| 认为外键自动建索引 | 删用户扫全表 | 手动 `CREATE INDEX ON todos(user_id)` |
