# 学习项 10 · N+1 Problem — 学习笔记

> 日期：2026-10-14
> 练习库：PostgreSQL `n1_practice_db`
> 练习文件：`practice.py`（6 练习全通 + 代码 Review）
> 演示脚本：`demo_n1.py`（N+1 现场）、`demo_fix.py`（三种写法 SQL 对比）

---

## 一、知识点讲解

### 1. 懒加载（lazy loading）—— N+1 的根源

`relationship()` 的默认行为是 `lazy="select"`：**不主动查，等你访问该属性时才发 SQL**。

```python
user = session.get(User, 1)     # SQL ①：SELECT * FROM users WHERE id = 1
print(user.name)                # 不发 SQL（数据已在对象里）
todos = user.todos              # SQL ②：SELECT * FROM todos WHERE user_id = 1  ← 偷偷发的
```

`user.todos` 看起来像普通属性，**底层是个 getter**（类似 JS 的 `Object.defineProperty` 取值时触发函数）。

**前端类比**
- 像 `<img loading="lazy">`：不进入视口就不加载；不碰 `.todos` 就不查库。
- 访问那一刻发 SQL ≈ 在 getter 里偷偷发请求。

**关键结论**：懒加载本身不是罪。**只要你不碰 `.todos`，一条多余 SQL 都不会发**（练习 1 证明了这点）。锅在「循环里反复碰它」。

---

### 2. N+1 到底是什么

```python
users = session.scalars(select(User)).all()   # 1 条
for u in users:
    print(u.todos)                            # N 条（每个用户各查一次）
```

**SQL 总数 = 1 + N**。

**前端类比 —— 就是你天天写的瀑布流请求**：

```javascript
const users = await fetch('/users').then(r => r.json());   // 1 次
for (const u of users) {
  const todos = await fetch(`/todos?user_id=${u.id}`);     // N 次 👈 同一个病
}
```

明明能一次拿完，却拆成 N 次往返。10 个用户 = 11 条 SQL，100 个用户 = 101 条。**N 越大越慢**。

**N+1 的「指纹」**（现场看到的）：

```sql
SELECT ... FROM todos WHERE %(param_1)s::INTEGER = todos.user_id
[generated] {'param_1': 1}     ← 同一个 SQL 模板
[cached]    {'param_1': 2}     ← 只换参数，执行 N 次
[cached]    {'param_1': 3}
```

> ⚠️ 日志里的 `[cached since ...]` 指的是 **SQL 语句编译结果**被缓存了，**不是查询结果被缓存**。库里照样老老实实查了 3 次。

---

### 3. 两种预加载（eager loading）

预加载 = **提前、批量**把关联数据拿回来，而不是等访问时才一条条查。

```python
# ① selectinload —— 应用层分两步
stmt = select(User).options(selectinload(User.todos))
users = session.scalars(stmt).all()
```

```sql
-- 第 1 条：先查用户，拿到 id
SELECT users.id, users.name FROM users;
-- 第 2 条：拿着这堆 id，一次问「谁的 user_id 在里面」
SELECT ... FROM todos WHERE todos.user_id IN (1, 2, 3);
```

**SQL = 2 条，与 N 无关。** 第 2 条必须等第 1 条出结果才能构造（不知道 id 就写不出 `IN (...)`），所以天然是两步。

```python
# ② joinedload —— 数据库层缝一张
stmt = select(User).options(joinedload(User.todos))
users = session.scalars(stmt).unique().all()      # ← 集合方向必须 .unique()
```

```sql
SELECT users.id, users.name, todos_1.title, ...
FROM users
LEFT OUTER JOIN todos AS todos_1 ON users.id = todos_1.user_id;
```

**SQL = 1 条。** 拼接是**数据库干的**，没有「第二步」的概念。

**一句话总结差异**：
> selectinload = **应用层分两步**；joinedload = **数据库层缝一张**。

---

### 4. 为什么 joinedload 需要 `.unique()`

`users LEFT JOIN todos` 的**原始结果是 9 行**（3 用户 × 3 todo），用户信息被**重复传了 3 遍**：

| 行 | users.id | users.name | todos.title |
|----|----------|-----------|-------------|
| 1 | 1 | 小明 | 小明的任务1 |
| 2 | 1 | **小明** | 小明的任务2 |
| 3 | 1 | **小明** | 小明的任务3 |
| ... | | | |

不加 `.unique()` → SQLAlchemy 2.0 直接报错：

```
InvalidRequestError: The unique() method must be invoked on this Result,
as it contains results that include joined eager loads against collections
```

**它不是优化，是强制要求。**

`.unique()` 干两件事：
1. 按 **User 主键**去重 → 3 个 User 对象（不是 9 个）
2. 把重复行挂着的 todo **合并进**那个 User 的 `.todos` 集合

**前端类比**（一模一样的逻辑）：

```javascript
const users = [...new Map(rows.map(r => [r.user_id, r])).values()];
```

**⚠️ 易误解**：`.unique()` 按「**主键相同**」合并，**不是**按「内容像」合并。两个 id 不同但标题都叫「买牛奶」的 Todo，不会被合并。

**为什么练习 5 不用 `.unique()`**：方向反过来（`todos JOIN users`），9 个 todo 各自只对应 1 个 user，**没有任何一行是重复的**。

---

### 5. 什么时候用哪个（判断依据）

| 场景 | 用谁 | 为什么 |
|------|------|--------|
| **一对多**（User → todos，孩子多） | `selectinload` | JOIN 会让行数翻倍膨胀 |
| **多对一 / 一对一**（Todo → user，就一个） | `joinedload` | 不放大行数，1 条最划算 |
| 根本不造对象（只要个数/统计） | 不用预加载，直接 `func.count` + `group_by` | 连对象都不用造 |

**记忆点：「多」的方向用 selectinload，「一」的方向用 joinedload。**

**为什么 joinedload 不能当默认**：
1. 不需要关联数据时，白白 JOIN 一大张表 → 浪费 DB I/O + 网络传输
2. 一对多会放大行数：3 用户 × 1000 todo = 3000 行，用户数据重复 3000 遍
3. **笛卡尔积爆炸**：同时 joinedload 两个一对多关系（todos × tags），JOIN 是**相乘**的 —— 3 × 1000 × 500 = **150 万行**，一条 SQL 干翻内存

→ 没有银弹，只有取舍。

---

### 6. 第三种路：聚合（不造对象）

只要「每人有几个 todo」这个**数字**时，造 9 个 Todo 对象纯属浪费。让数据库数：

```python
stmt = select(User.name, func.count(Todo.id)).join(Todo).group_by(User.name)
rows = session.execute(stmt).all()
return {name: cnt for name, cnt in rows}
```

对应 SQL：

```sql
SELECT users.name, COUNT(todos.id)
FROM users JOIN todos ON users.id = todos.user_id
GROUP BY users.name;
```

**两个新 API**：

| | `session.scalars(stmt)` | `session.execute(stmt)` |
|---|---|---|
| 取几列 | 只取**第一列** | 取**所有列** |
| 返回 | 模型对象（`User`） | `Row` 对象 |

`Row` 可以像元组一样解包：`for name, cnt in rows`（也支持 `row.name` / `row[1]`）。

**SQL = 1 条，全程零对象构造。**

---

## 二、练习 ↔ 知识点映射

| 练习 | 函数 | 对应知识点 | 期望 SQL |
|------|------|-----------|---------|
| 1 | `get_all_user_names` | 懒加载不主动触发（反证） | 1 条 |
| 2 | `get_users_with_todos_naive` | **亲手复现 N+1** | 1 + N = 4 条 |
| 3 | `get_users_with_todos_selectin` | 一对多 → selectinload | 2 条 |
| 4 | `get_users_with_todos_joined` | 一对多 → joinedload + `.unique()` | 1 条 |
| 5 | `get_todos_with_user_joined` | 反方向：多对一 → joinedload，**不用** `.unique()` | 1 条 |
| 6 | `count_todos_per_user` | 聚合 `func.count` + `group_by` + `execute` | 1 条 |

**测试的特殊之处**：每题都断言**两件事** —— 结果对不对 **+ SQL 条数对不对**。光结果对不算过。

**基础设施**（文件里已给好，不用写）：`engine` / `Base` / `User` / `Todo` 模型 / `track_sql()` / `run_counting()` / `seed()`。

SQL 计数原理：用 `@event.listens_for(engine, "before_cursor_execute")` 挂钩子，把每条真实执行的 SQL 抓下来（过滤掉 BEGIN/ROLLBACK/COMMIT）。

---

## 三、练习纠错全记录

### 🔴 探底问答（本节开头）—— 暴露对懒加载的误解

**现象**：问「`session.get(User, 1)` / `print(user.name)` / `[t.title for t in user.todos]` 三行各发不发 SQL？」，回答「第一行发了，后面两行没发」；问「10 个用户循环访问 todos 共几条 SQL？」，回答「两条」。

**正确答案**：第三行**会发** SQL（懒加载触发），三行共 2 条；10 个用户共 **11 条**。

**原因**：以为 `user.todos` 是「早就存在内存里的 list」。

**对应知识点**：懒加载 `lazy="select"` —— `relationship` 是个 getter，访问那一刻才查库。

**解决**：用 `demo_n1.py` 亲眼看到 4 条 SQL，确认「同一个 SQL 模板换参数执行 N 次」的指纹。

---

### 练习 1：`session.get(User)` —— 学习项 6 的「get 特例」忘了

**现象**：

```python
users = session.get(User)          # TypeError: missing 1 required positional argument: 'ident'
return [u.name for u in users]
```

**原因**：忘了 `session.get` 的语义。**用户明确表示「不记得了」**，直接讲解。

**对应知识点**：`session.get(模型类, 主键值)` ——
- 要 **2 个参数**（`(模型类, 主键值)`）
- 只返回 **1 个对象**（或 `None`），**不是 list**
- 是唯一的「特例」：跳过 `select()` 构造那一步，一句话直接给对象
- 会**先查内存缓存**（identity map），已加载过就连 SQL 都不发
- 底层：`SELECT * FROM users WHERE id = 1`

**解决**：改用常规姿势 —— `session.scalars(select(User)).all()`。

---

### 练习 2：两个错连在一起

**现象 ①**：

```python
kk = []
for u in users:
    kk[u.name] = u.todos     # TypeError: list indices must be integers or slices, not str
```

**原因 ①（shape 问题）**：`kk` 要装的是「**名字 → 标题列表**」的**映射**，`[]` 装不下映射。**学习项 9 同款错误家族** —— 当时连续两次「拿错层」。

**解决 ①**：`kk = {}`。

**现象 ②**：改成 `{}` 后结果对不上 —— 值是一堆 Todo 对象，不是标题字符串。

**原因 ②**：`u.todos` 给的是 **Todo 对象列表**，要的是**字符串列表**。用户**不会写列表推导式**（说「不会了，教教我」）。

**解决 ②**：`[t.title for t in u.todos]`

```javascript
user.todos.map(t => t.title)     // JS
[t.title for t in u.todos]       // Python
```

**最终**：断言通过，SQL = **4 条**（1 + 3）。N+1 复现成功。

---

### 练习 3：漏 `.all()`（第 2 次）

**现象**：`session.scalars(select(User).options(selectinload(User.todos)))` —— 末尾没 `.all()`，但测试**居然过了**。

**原因**：`session.scalars()` 返回 `ScalarResult`，**它是可迭代的**，紧跟着的 `for` 循环把它消费掉了，所以没暴露问题。

**对应知识点**：
- `session.scalars(stmt)` → `ScalarResult`（**惰性**，SQL 可能到遍历时才执行）
- `session.scalars(stmt).all()` → `list`（数据已到手）
- 隐患：`return` 一个 `ScalarResult`，调用方在 **session 关闭后**才遍历 → 报错

**解决**：补 `.all()`。**记账：这是第 2 次**（学习项 6 的 `top` 是第 1 次，练习 5 是第 3 次）。

---

### 练习 4：✅ 一次过

`joinedload` + `.unique().all()`，SQL = 1 条。

---

### 练习 5：一行里三个错

**现象 ①（语法层）**：

```python
return [t.name, t.user for t in todos]
# SyntaxError: 整个文件跑不起来
```

**原因 ①**：中括号里要么放**一个**表达式，要么放「表达式 + `for` 从句」，不能「A, B + `for` 从句」。每个元素是一个**元组**，需要一层括号。

**现象 ②（属性名）**：

```python
AttributeError: 'Todo' object has no attribute 'name'
```

**原因 ②**：Todo 类只有 `id` / `title` / `user_id` / `user`，**没有 `name`**。要的是 `title`。

**学会读 AttributeError**：

```
AttributeError: '哪个类' object has no attribute '哪个属性'
```

**现象 ③（类型）**：`t.user` 给的是整个 User **对象**，要的是**字符串**。

**现象 ④**：没有 `return` —— 写成 `print(todos)`，函数隐式返回 `None`，测试报「实际 None」。

**对应知识点**：Python 里**函数没写 return 就返回 None，这是合法的**（不像 JS 的 `undefined` 那么扎眼）。所以「实际 None」几乎永远 = 「你忘写 return 了」。

**解决**：

```python
todos = session.scalars(select(Todo).options(joinedload(Todo.user))).all()
return [(t.title, t.user.name) for t in todos]
```

**SQL = 1 条。**（顺手也补上了第 3 次漏掉的 `.all()`）

---

### 练习 6：字典推导式里两个名字对不上

**现象**：

```python
return {name: cnt for rows, cnt in rows}
# NameError: name 'name' is not defined
```

**原因**：`for` 里解包出来的变量叫 `rows, cnt`，冒号左边却用了 `name` —— **同一个东西起了两个名字，对不上**。而且 `rows` 既是被遍历的对象又是循环变量，很绕。

**对应知识点**：

```python
{ 键 : 值   for  变量A, 变量B  in  可迭代对象 }
   ↑              ↑
  这里用的名字，必须是 for 里解包出来的名字
```

**解决**：`return {name: cnt for name, cnt in rows}`。

---

### 🔴 代码 Review（全绿之后）

| # | 问题 | 原因 | 改法 |
|---|------|------|------|
| ① | 练习 3 漏 `.all()` | 惰性结果被 for 循环消费掉了，侥幸能跑 | 补 `.all()`，养成肌肉记忆 |
| ② | 变量名 `kk`（三处） | 名字没传递任何信息 | 改成 `result` |
| ③ | 练习 6 一行 162 字符 | 「构造 + 执行 + 取结果」挤在一起 | 拆成 `stmt = ...` / `rows = ...` 两步 |
| ④ | `smt` 拼写 | 应是 `stmt`（statement） | 顺手改 |

**命名心法**：变量名要回答「**这里面装的是什么**」。`kk` / `data` / `tmp` / `res` 都是偷懒。

**拆行心法**：「构造」和「执行」永远是两步 —— 拆开写，代码自己就把学习项 6 的心法讲清楚了。

---

## 四、踩坑速查表

| 错误写法 | 报错 / 现象 | 正确写法 |
|---------|------------|---------|
| `session.get(User)` | `TypeError: missing 1 required positional argument: 'ident'` | `session.get(User, 1)`（要主键）或 `session.scalars(select(User)).all()`（要多条） |
| `[u.name for u in user]`（user 是单个对象） | `TypeError: 'User' object is not iterable` | 对象不能遍历，先用 `.all()` 拿成 list |
| `kk = []` 然后 `kk[u.name] = v` | `TypeError: list indices must be integers or slices, not str` | 装映射用 `kk = {}` |
| `kk[u.name] = u.todos` | 结果里全是 Todo 对象，不是字符串 | `kk[u.name] = [t.title for t in u.todos]` |
| `session.scalars(stmt)` 直接进 for | 侥幸能跑，但 `ScalarResult` 是惰性的 | 一律接 `.all()`（`scalars` 后不接 `.first()`/`.unique()` 时） |
| `joinedload(集合)` 不接 `.unique()` | `InvalidRequestError: The unique() method must be invoked on this Result...` | `session.scalars(stmt).unique().all()` |
| `[t.name, t.user for t in todos]` | `SyntaxError`（整个文件跑不起来） | `[(t.title, t.user.name) for t in todos]` |
| `t.name`（Todo 对象） | `AttributeError: 'Todo' object has no attribute 'name'` | Todo 的属性是 `title` |
| 函数只 `print` 不 `return` | 测试报「**实际 None**」 | Python 没写 return 就返回 `None`，检查是不是忘写了 |
| `{name: cnt for rows, cnt in rows}` | `NameError: name 'name' is not defined` | `for name, cnt in rows` —— 名字必须和左边对上 |
| 命令前面打全角 `！` | `!` 前缀命令不生效 | 切英文输入法打半角 `!`（和弯引号 `‘ ’` 是同一个病） |

---

## 五、本节生成的文件

| 文件 | 作用 |
|------|------|
| `practice.py` | 6 道练习（含 TODO 与自动测试，每题断言结果 + SQL 条数） |
| `demo_n1.py` | N+1 现场：3 用户 × 3 todo，`echo=True` 打印真实 SQL |
| `demo_fix.py` | 三种写法对比：懒加载 4 条 / selectinload 2 条 / joinedload 1 条 |
| `notes.md` | 本文件 |

练习库：`n1_practice_db`（`createdb n1_practice_db`）

运行方式：

```bash
.venv/bin/python 2数据持久化/10N+1Problem/practice.py
```
