# 学习项 6 · SQLAlchemy 2.0 — 笔记

> 学习日期：2026-08-27 ｜ 7 个练习全通 ✅
> 本节核心：用「Python 对象」操作数据库，不写 SQL 字符串。

---

## 一、知识点讲解

### 1. ORM 是什么（核心观念转变）

ORM = Object-Relational Mapping（对象关系映射）。一句话：**把「表」写成「类」，用对象操作数据库，不写 SQL 字符串。**

| 数据库 | ORM | 前端类比 |
|--------|-----|---------|
| 表 table | 类 `class User` | React 组件 |
| 行 row | 对象 `User(name=...)` | 一个 state 对象 |
| 列 column | 类属性 `User.name` | props / 字段 |
| SQL 语句 | 方法调用 `.add()` `.commit()` | 调 API |

学习项 5 是面向字符串（`cur.execute("INSERT...")`），学习项 6 面向对象。

### 2. SQLAlchemy 2.0 vs 1.4（时代分界线）

| | 1.4 旧写法 | **2.0 新写法（学的）** |
|---|---|---|
| 基类 | `declarative_base()` | `class Base(DeclarativeBase)` |
| 定义列 | `Column()` | **`Mapped[类型]` + `mapped_column()`** |
| 查询 | `session.query(User)` | **`select()`** |

`Mapped[int]` = 0.3 学的 `def foo(x: int)` 同一套类型提示语法，复用。

### 3. 模型定义：`Mapped[...]` 方括号 = 列类型

| 你写 | SQL 类型 |
|------|---------|
| `Mapped[int]` | `INTEGER` |
| `Mapped[str]` | `VARCHAR` |
| `Mapped[bool]` | `BOOLEAN` |

- `Mapped[x]`（非 Optional）= 列**非空**（NOT NULL）；`Mapped[x \| None]` 才允许 NULL。
- `mapped_column()` 是列选项：`primary_key=True`（主键）、`ForeignKey(...)`（外键）、`default=...`（默认值）。
- 类名单数（`User`），表名复数（`__tablename__ = "users"`）。

### 4. Session：操作数据库的「工作台」

- `session.add(obj)` = 把内容写进**草稿**（还在内存）
- `session.commit()` = **提交保存**（真正写库，**无参**）
- 不 commit，草稿就丢，数据库不变。

一个 Session 是一个工作单元（Unit of Work），为一堆改动服务，最后一起 commit —— 为后续「Transactions / ACID」铺垫。

### 5. 查询：`select()` 构造 ≠ 执行（本课最重要的坑）

```
stmt = select(User).where(...)     # ① 构造蓝图（没碰数据库）
res  = session.execute(stmt)       # ② 执行！（真正查库）
user = res.scalars().first()       # ③ 取结果
```

| 函数 | 作用 |
|------|------|
| `select(...)` | **构造**语句（蓝图）—— 接 `.where/.order_by/.limit/.desc/.contains` 继续构造 |
| `session.execute(...)` | **执行** |
| `.scalars()` | 行 → 对象；`.first()` 取 1 个 / `.all()` 取全部 |
| `.scalar()` | 取**单个标量值**（如 count 的数字） |

**特例**：`session.get(User, id)` 是「按主键瞬取」的捷径，**自带执行、直接返回对象**，不要再 execute！

### 6. relationship 一对多（本课的灵魂）

外键（`ForeignKey`）= 数据库「怎么存」；relationship = 代码「怎么拿」（不用写 JOIN）。

```python
class User(Base):
    todos: Mapped[list['Todo']] = relationship(back_populates="user")   # 一端：一个用户一堆待办（list）

class Todo(Base):
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))        # 数据层外键
    user: Mapped['User'] = relationship(back_populates="todos")         # 另一端：一份待办一个用户（单个）
```

要点：
- **两端互为镜像**，缺一不可；`back_populates` 名字两端**严格互相对应**（`"user"` ↔ 属性 `user`，`"todos"` ↔ 属性 `todos`）。
- 类型方向相反：User 端是 `list["Todo"]`（一对多），Todo 端是 `"User"`（多个对一）。
- `back_populates` 的魔力：**自动同步**。`user.todos.append(t1)` 会自动填 `t1.user`、`t1.user_id`，不用手动设。

---

## 二、练习 ↔ 知识点映射

| 练习 | 知识点 |
|------|--------|
| 1 模型定义 | DeclarativeBase、Mapped、mapped_column、主键、类型→SQL 映射 |
| 2 Session 新增 | `User(...)` + add + commit；聚合 `select(func.count()).select_from()` + scalar |
| 3 Session 查询 | `session.get()`；`select().where().scalars().first()` |
| 4 Session 更新 | 改对象属性 + commit（不写 UPDATE）|
| 5 Session 删除 | `session.delete()` + commit（不写 DELETE）|
| 6 select 高级查询 | contains / order_by / desc / limit / scalars().all() |
| 7 一对多关系 | ForeignKey + relationship / back_populates / user.todos 导航 |

---

## 三、练习纠错全记录（这条轨迹最值钱）

### 坑 1：`select()` 是「构造」不是「查询」（反复犯）

- **现象**：`return select(User).where(...)` 后，`fe.name` 报 `'Select' object has no attribute 'name'`；`count_users` 也是 `return select(func.count())`。
- **原因**：把「查询蓝图」当成了「查询结果」返回。
- **知识点**：`select()` 只是构造 SQL 语句对象，必须 `session.execute()` 才真正查库。
- **解决**：`session.execute(select(...)).scalars().first()`。

### 坑 2：`session.get()` 是特例，别再 execute

- **现象**：`stmt = session.get(User, id); res = session.execute(stmt)` → `ArgumentError: got <User object>`。
- **原因**：`get` 已经返回结果（User 对象），又拿去 execute。
- **知识点**：`get` 自带执行、一步到位；只有 `select()` 构造的才算「待执行的蓝图」。
- **解决**：`return session.get(User, user_id)`。

### 坑 3：count 忘指定表 + 忘取数字

- **现象**：`select(func.count())` 执行后返回 `CursorResult`（不是 2），且 POSTGRES 把它当 `SELECT count(*)` **没有 FROM**，恒返回 1。
- **原因**：没 `.select_from(User)`（不知道数哪张表）；`return res` 返回容器不是数字。
- **知识点**：`select(func.count()).select_from(User)`；取数字用 `.scalar()`。
- **验证**：无 select_from → 1；有 select_from → 2。

### 坑 4：`.scalars()` 挂错了对象

- **现象**：`select(func.count()).select_from(User).scalars()` → `AttributeError: 'Select' object has no attribute 'scalars'`。
- **原因**：`.scalars()/.scalar()/.all()/.first()` 是 **execute 返回的 Result** 上的方法，不是 `select()` 蓝图上的。
- **知识点**：构造方法归 `select()`，取值方法归 `Result`。

### 坑 5：`commit()` 传参

- **现象**：`session.commit(user)` → `TypeError: Session.commit() takes 1 positional argument but 2 were given`。
- **原因**：`commit()` **无参**，提交整个会话的改动，不针对某个对象。
- **解决**：`session.commit()`。

### 坑 6：更新成功分支忘记 `return True`

- **现象**：`update_email` 改完 email 后没 return，函数返回 `None`，`if not ok` 判失败。
- **解决**：if 分支 commit 后补 `return True`（else 分支 return False 已有）。

### 坑 7：execute 传错对象（list_users_by_name）

- **现象**：构造了 `stmt`，却 `res = session.execute(User.name)`（传了列对象，不是语句）。
- **解决**：`session.execute(stmt)`。

### 坑 8：`scalars()` 后忘了 `.all()`（top_users）

- **现象**：`return res.scalars()`，`len(tops)` 报 `TypeError`。
- **原因**：`.scalars()` 返回的是可迭代器，不是 list。要 `.all()` 才变列表。
- **解决**：`return res.scalars().all()`。

### 坑 9：relationship 只写了一端 + 忘 import

- **现象**：`NameError: name 'relationship' is not defined`（用了但没 import）；且只给 `User` 写了关系、`Todo` 类没有。
- **原因**：import 行缺 `relationship`；关系是**镜像两端**，只在 User 端写、Todo 端缺，关系连不起来。
- **解决**：import 补 `relationship`；`Todo` 类补 `user_id` 外键 + `user = relationship(back_populates="todos")`。

### 坑 10：`done` 非空列没给默认值

- **现象**：`Todo(title='写笔记')` 报 `NotNullViolation: null value in column "done"`。
- **原因**：`Mapped[bool]` = NOT NULL，插入时 `done` 为 null。
- **解决**：`done: Mapped[bool] = mapped_column(default=False)`（新待办默认未完成，合理）。

### 坑 11：把 relationship 属性名改了（最有教训的一个）

- **现象**：把 `todos/user` 改成 `rela_todos/rela_user`，两端虽然自洽，但测试 `hasattr(main, "todos")` 判失败、`user.todos` 报 AttributeError。
- **原因**：relationship 属性名是**对外契约**，必须是调用方（测试/其他代码）约定的名字；单方面改名会让调用方找不到。
- **知识点**：属性名 = 你访问它的名字 = 与外部约定的接口名，不能随意加前缀。
- **解决**：改回约定名 `todos` / `user`（测试代码写死了 `main.todos`，不可改）。

> 🧠 前端类比：组件规定 props 叫 `data`，你改成 `info` 后父组件传的 `data` 就接不到了。属性名是两边的契约。

---

## 四、踩坑速查表

| 错误写法 | 报错 | 正确写法 |
|---------|------|---------|
| `return select(User)` | `'Select' object has no attribute 'name'` | `session.execute(select(User)...).scalars().first()` |
| `stmt = session.get(...)` 再 `execute(stmt)` | `got <User object>` | 直接 `return session.get(...)` |
| `select(func.count())` | 返回 1（无 FROM）| `select(func.count()).select_from(User)` |
| `return res`（execute 后） | 不是数字/列表 | `res.scalar()` 或 `res.scalars().all()` |
| `session.commit(user)` | `commit() takes 1 position arg but 2 were given` | `session.commit()` |
| `select(...).scalars()` | `'Select' object has no attribute 'scalars'` | `session.execute(...).scalars()` |
| `res.scalars()` 当 list | `TypeError: object has no len()` | `res.scalars().all()` |
| `execute(User.name)` | `got <User object>` | `execute(stmt)` |
| 只用 `relationship` 未 import | `NameError: relationship not defined` | 加进 import |
| relationship 只写一端 | 关系连不上 | 两端都写，back_populates 互相对应 |
| `Mapped[bool]` 不给值 | `NotNullViolation on column done` | `mapped_column(default=False)` |
| 改掉关系名 `todos`→`rela_todos` | `hasattr(main,'todos')` 失败 | 属性名保持约定名 `todos`/`user` |

---

## 五、一句话总结

> **建模用 `Mapped` + `mapped_column`（2.0），读写靠 `Session`，查询记住「select 构造 → execute 执行 → scalars/scalar 取值」，关系靠 `relationship` 两端镜像成对出现且名字是契约。**
