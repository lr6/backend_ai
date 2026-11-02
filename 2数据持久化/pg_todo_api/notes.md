# 阶段项目 · PostgreSQL Todo API — 学习笔记

> 完成日期：2026-11-02
> 环境：FastAPI 0.143 / SQLAlchemy 2.1 / Alembic 1.20 / psycopg 3.3 / PostgreSQL
> 数据库：`todo_api_db`
> 项目目录：`2数据持久化/pg_todo_api/`

---

## 一、项目结构（请求链路）

```
HTTP JSON
   ↓
schemas.py     Pydantic 请求模型（UserCreate / TodoCreate / TodoUpdate）
   ↓
main.py        路由函数（Depends(get_db) 注入 Session）
   ↓
models.py      SQLAlchemy ORM 模型（User / Todo）
   ↓
database.py    engine / SessionLocal / get_db
   ↓
PostgreSQL     users / todos / alembic_version
```

```
main.py        ──import──→ models.py ──import──→ database.py
schemas.py     （不被 models 反向依赖，避免循环引用）
alembic/env.py ──import──→ database.Base + models（注册表）
```

---

## 二、知识点讲解

### Task 1 · database.py — 数据库连接与请求级 Session

| 组件 | 作用 | 关键点 |
|------|------|--------|
| `engine` | 连接池，管"怎么连数据库" | `create_engine(DATABASE_URL, echo=True)`；Docker/生产要配 pool |
| `SessionLocal` | Session 工厂（不是 Session 本身） | `sessionmaker(bind=engine)`，调用才产出 Session |
| `get_db` | FastAPI 依赖，每个请求一个 Session | 生成器函数：`yield` 前开场，`finally` 里 `db.close()` |

```python
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- `yield` 语义与学习项 3 的 lifespan 相同：`yield` 前 = 开场，`yield` 后 = 收场
- `finally` 保证**成功或异常**都归还连接
- 验证方式：`engine.pool.checkedout()` 收场前后对比

### Task 2 · models.py — ORM 模型与关系

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    email: Mapped[str | None] = mapped_column(String(100))

    todos: Mapped[list["Todo"]] = relationship(back_populates="user")


class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    done: Mapped[bool] = mapped_column(default=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    user: Mapped["User"] = relationship(back_populates="todos")
```

核心规则：

1. **`mapped_column` 管列，`relationship` 管属性；两者平级，不能嵌套**
2. **外键放在「多」的一方**：`todos.user_id → users.id`
3. **`ForeignKey("users.id")` 用表名.列名**（数据库世界）
4. **`back_populates` 用对面类里的属性名**（Python 世界）
   - `User.todos → "user"`：Todo 里指向 User 的属性叫 `user`
   - `Todo.user → "todos"`：User 里指向 Todo 的属性叫 `todos`
5. 前向引用要加引号：`Mapped[list["Todo"]]`、`Mapped["User"]`
6. `Mapped[str | None]` → 自动 `nullable=True`；`Mapped[bool]` → 自动 `NOT NULL`

### Task 3 · Alembic — 数据库迁移

| Git | Alembic |
|-----|---------|
| `git diff` | `alembic revision --autogenerate` |
| commit 历史 | 迁移文件链（`revision` / `down_revision`） |
| `git log` | `alembic history` |
| 应用改动 | `alembic upgrade head` |
| 撤销 | `alembic downgrade -1` |

#### 两处核心配置

| 配置 | 文件 | 作用 |
|------|------|------|
| `sqlalchemy.url` | `alembic.ini` | 连哪个数据库 |
| `target_metadata` | `alembic/env.py` | 模型结构基准 |

```python
# alembic/env.py
from database import Base
import models  # noqa: F401 —— 关键：import 触发类定义，表才注册进 metadata

target_metadata = Base.metadata
```

**关键坑**：只 `from database import Base` 不够。`Base.metadata` 是注册表，必须 import 模型模块执行类定义，表才会登记进去。

#### autogenerate 是差异驱动

```
Base.metadata（模型） vs 数据库现状 → 差异 → 迁移文件
```

- 有差异：`Detected added table 'users'` / `Detected added table 'todos'`
- 无差异：生成空迁移（`upgrade()` / `downgrade()` 只有 `pass`）
- `Detected sequence named 'users_id_seq' ... assuming SERIAL and omitting` = PG 自增序列噪音，**不是差异**
- 判断标准：只看 `Detected added ...` 行

#### 本次生成的迁移

```
revision     = 15d1276d1b94
down_revision = None        # 第一条迁移
upgrade():    先建 users，再建 todos（先被引用方）
downgrade():  先删 todos，再删 users（倒着拆）
```

`alembic_version` 表由 Alembic 自动创建，记录当前版本；`alembic current` 从它读。

### Task 4 · schemas.py — 三层模型

| 模型 | 方向 | 职责 |
|------|------|------|
| SQLAlchemy `Todo` | Python ↔ 数据库 | 映射表结构 |
| Pydantic `TodoCreate` | 客户端 → 服务端 | 校验输入，只含可写字段 |
| Pydantic `TodoRead` | 服务端 → 客户端 | 决定返回哪些字段 |

不直接返回 ORM 对象的原因：避免泄露字段、避免 API 被表结构绑架、输入输出职责分离。

```python
class TodoCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    user_id: int


class TodoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # 允许从 ORM 对象读属性

    id: int
    title: str
    done: bool
    user_id: int


class TodoUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None
```

`Field` 只有在**传参数**时才有意义；`Field()` 空壳等于没写。

### Task 4 · main.py — CRUD 路由

| 操作 | 模式 |
|------|------|
| 依赖注入 | `db: Session = Depends(get_db)` |
| 创建 | `models.X(**payload.model_dump())` → `db.add` → `db.commit` → `db.refresh` |
| 查单个 | `db.get(models.X, id)`；`None` → `raise HTTPException(404, ...)` |
| 列表 | `stmt = select(models.X)`；有筛选才 `where`；`db.scalars(stmt).all()` |
| 部分更新 | `payload.model_dump(exclude_unset=True)` → `for k,v` `setattr` → commit/refresh |
| 删除 | `db.delete(obj)` → `db.commit()`；返回 204 |
| 状态码 | 创建 201、删除 204、找不到 404 |

#### 可选筛选参数的正确写法

```python
stmt = select(models.Todo)
if user_id is not None:                    # ✅ 不能用 if user_id:
    stmt = stmt.where(models.Todo.user_id == user_id)
if done is not None:                       # False 是合法值
    stmt = stmt.where(models.Todo.done == done)
return db.scalars(stmt).all()
```

原因：`models.Todo.user_id == None` 会编译成 `user_id IS NULL`，不是"忽略该条件"。而 `user_id` / `done` 都是 NOT NULL 列 → 查询永远为空。

#### PATCH 的 exclude_unset

区分「没传」和「传了假值（False / 0 / ""）」：

```python
payload.model_dump()                    # {"title": None, "done": True} —— 没传的也变成 None
payload.model_dump(exclude_unset=True)  # {"done": True}                —— 只含客户端传了的
```

---

## 三、练习 ↔ 知识点映射

| 文件 / 测试 | 覆盖知识点 |
|-------------|-----------|
| `database.py` 3 个测试 | engine 连通、get_db 生成器、finally 归还连接 |
| `models.py` 4 组测试 | metadata 注册、列/唯一约束/可空、外键、双向关系 |
| Alembic 迁移 | autogenerate 差异驱动、升级、版本表 |
| `schemas.py` 8 个测试 | 请求/响应模型、Field 约束、from_attributes |
| `main.py` 22 个断言 | Depends、CRUD、404、201/204、404、exclude_unset |
| uvicorn + curl | 真服务器验证完整链路 |

---

## 四、本次会话纠错全记录

### 问题 1：`mapped_column(relationship(...))` 套娃（连踩 2 次）

- **现象**：`ArgumentError: 'SchemaItem' object ... expected, got <_RelationshipDeclared>`
- **原因**：`mapped_column` 只接收数据库列（Column / Constraint），`relationship` 是属性声明，不是列
- **过程**：第一次改好 `Todo` 那行，却把 `User` 那行改坏了（改了这边坏那边）
- **解决**：两处都写成裸 `relationship(...)`
- **规则**：`mapped_column` 管列，`relationship` 管属性，两者平级，不能嵌套

### 问题 2：`back_populates` 不知道填什么

- **探底**：问「Todo 属性改名 owner 后，User.todos 填什么？」——猜中 "owner" 但不理解
- **讲解**：`back_populates` = 对面类里那个属性的名字（不是表名、不是类名）
- **解决**：
  - `User.todos` → `"user"`
  - `Todo.user` → `"todos"`

### 问题 3：`ForeignKey("users.id")` 里为什么是 users 不是 User

- **原因**：混了 Python 世界和数据库世界
  - `ForeignKey` 最终生成 DDL `REFERENCES users(id)` → 用**表名.列名**
  - `relationship` / 类型注解是 Python → 用**类名 / 属性名**
- **检查题**：类名改成 `Account`、`__tablename__` 仍是 `"users"` → `"users.id"` 不用改，`Mapped["User"]` 要改
- 答对

### 问题 4：`if user in None:` → TypeError

- **现象**：`TypeError: argument of type 'NoneType' is not iterable`
- **原因**：`in` 右边必须是容器；判断 None 应使用身份比较
- **解决**：`if user is None:`

### 问题 5：`db.get(models.User, user_id)` 用了不存在的变量

- **现象**：测试期望 404，实际 `IntegrityError: ... violates foreign key constraint`
- **原因**：`create_todo` 没有 `user_id` 参数，Python 去模块全局找到了测试块的 `user_id`，导致校验的是"刚创建的用户"而不是 `payload.user_id`
- **解决**：`db.get(models.User, payload.user_id)`
- **教训**：变量名看着对不代表作用域对；全局变量会掩盖 NameError

### 问题 6：`db.refresh()` 忘传实例

- **现象**：`TypeError: Session.refresh() missing 1 required positional argument: 'instance'`
- **解决**：`db.refresh(todo)`

### 问题 7：列表查询无条件 `where`

- **现象**：测试没暴露；`GET /todos` 不传参数会返回空列表
- **原因**：`models.Todo.user_id == None` → `IS NULL`，NOT NULL 列永远不匹配
- **解决**：`if user_id is not None:` 才加 where
- **教训**：测试全绿 ≠ 正确，测试没覆盖的分支要对照 docstring 检查

### 问题 8：`if done:` 还是 `if done is not None:`

- **场景**：`GET /todos?done=false`
- **答案**：必须 `is not None`
- **原因**：`False` 是合法值但为假值，`if done:` 会把它当成"没传"，漏掉筛选

### 问题 9：Pydantic `Field()` 空壳 / 漏 `min_length`

- **现象**：`user_id: int = Field()` 多余；`title: str = Field(max_length=200)` 允许空字符串
- **解决**：无参数就不写 `Field`；约束写全 `min_length=1, max_length=200`

---

## 五、踩坑速查表

| 错误写法 / 场景 | 报错 / 现象 | 正确写法 |
|----------------|------------|---------|
| `mapped_column(relationship(...))` | `ArgumentError: ... got <_RelationshipDeclared>` | `relationship(...)` |
| `ForeignKey("User.id")` | 迁移/建表找不到目标表 | `ForeignKey("users.id")` |
| `back_populates="todos"` 写在 User.todos 上 | 关系镜像不对 / 测试失败 | 填**对面属性名** `"user"` |
| `if user in None:` | `TypeError: NoneType is not iterable` | `if user is None:` |
| `db.refresh()` | `TypeError: missing ... 'instance'` | `db.refresh(obj)` |
| 路由里用未定义的变量 | `NameError`，或误用全局变量导致 SQL 错误 | 用 `payload.xxx` |
| `where(col == None)` | 编译成 `IS NULL`，结果为空 | `if x is not None: where(...)` |
| `if done:` 判断可选参数 | `done=false` 被当成没传 | `if done is not None:` |
| `model_dump()` 用在 PATCH | 没传的字段被 None 覆盖 | `model_dump(exclude_unset=True)` |
| `Field()` 无参数 | 无效果（不是错，但多余） | 直接写类型注解 |
| autogenerate 无 `Detected added` | 空迁移（只有 pass） | 确认模型与库确实无差异 |
| `env.py` 没 import models | metadata 为空，autogenerate 无表 | `import models  # noqa: F401` |
| `alembic` command not found | macOS venv 路径为 `bin/` | `.venv/bin/alembic` |

---

## 六、常用命令速查

```bash
# 建库（本次已存在）
createdb todo_api_db

# 迁移
.venv/bin/alembic init alembic
.venv/bin/alembic revision --autogenerate -m "create users and todos"
.venv/bin/alembic upgrade head
.venv/bin/alembic current
.venv/bin/alembic history
.venv/bin/alembic downgrade -1

# 运行测试（各文件末尾）
.venv/bin/python database.py
.venv/bin/python models.py
.venv/bin/python schemas.py
.venv/bin/python main.py

# 启动服务
.venv/bin/uvicorn main:app --reload
# Swagger: http://127.0.0.1:8000/docs

# 查看表
psql -d todo_api_db -c "\dt"
psql -d todo_api_db -c "\d todos"
```

---

## 七、待改进（留到后续阶段）

1. `POST /users` 用户名重复 → 目前抛 `IntegrityError` 返回 500，应捕获并返回 **409 Conflict**
2. `database.py` 与 `alembic.ini` 各存一份数据库 URL → 可统一为单一真相来源
3. 测试目前写在 `if __name__ == "__main__"` 里 → 后续学习项 17/18 改成 pytest
4. 尚未加分页（学习项 2 的分页设计）；`GET /todos` 数据量大时需要 `limit/offset`

---

## 八、补充：从项目文件理解后端分层（2026-11-02 讨论）

### 1. 四个文件的职责

| 文件 | 职责 | 层次 |
|------|------|------|
| `main.py` | 定义路由、处理请求、返回响应；创建 `FastAPI` 实例 | HTTP 层 / 入口 |
| `schemas.py` | 校验请求数据、决定响应字段 | API 契约层（DTO）|
| `models.py` | 定义数据库表、列、外键、关系 | 持久化模型层（Entity）|
| `database.py` | 连接池、Session 工厂、`get_db` | 基础设施层 |

### 2. 依赖方向

```
main.py ──────→ schemas.py
   │
   ├──────────→ models.py ──────→ database.py
   │
   └──────────→ database.py（get_db）
```

- `database.py` 不 import 任何项目模块（避免循环引用）
- `models.py` 只依赖 `database.Base`
- `schemas.py` 不依赖项目文件
- `main.py` 依赖上面三个

### 3. 入口文件

**`main.py` 是 Web 应用入口**：

```bash
uvicorn main:app --reload
#        ↑    ↑
#      模块   FastAPI 实例变量
```

uvicorn 会 import `main`、执行 `app = FastAPI(...)`、注册路由，然后监听端口。

其他文件不是入口：

- `database.py` / `models.py` / `schemas.py` 都是被 import 的模块
- 各文件末尾的 `if __name__ == "__main__":` 是学习用的测试块，不是应用入口
- Alembic 是独立的 CLI 入口：`alembic.ini` → `alembic/env.py`

### 4. Controller（控制器）

`main.py` 里**带路由装饰器的函数**才是 controller：

```python
@app.post("/todos")
def create_todo(payload, db):
    ...
```

同一个文件里的其他代码不算 controller：

| 代码 | 是什么 |
|------|--------|
| `app = FastAPI(...)` | 应用实例 / 组装 |
| `import models, schemas` | 依赖声明 |
| `@app.post(...)` | 路由注册 |
| `def create_todo(...)` | controller |
| `if __name__ == "__main__":` | 测试块 |

所以现阶段 `main.py` 同时承担「应用组装」和「controller 层」两个角色，小项目这样没问题。

### 5. 除 controller 外的常见分层

| 层 / 角色 | 职责 | 当前项目状态 |
|-----------|------|-------------|
| Router | 把一组路由挂到 app | 未拆，直接 `@app.get` |
| Controller | 接请求 → 调业务 → 返回响应 | `main.py` 路由函数 |
| Service | 业务逻辑、组合多个操作 | 未拆，目前写在 controller |
| Repository / DAO | 只负责数据库读写 | 未拆，controller 直接 `db.get` / `select` |
| Model / Entity | 数据库表结构 | `models.py` |
| Schema / DTO | 请求/响应结构 + 校验 | `schemas.py` |
| Middleware | 请求前后统一处理（日志、鉴权、CORS）| 未使用 |
| Dependency | 请求级可复用依赖（Session、当前用户）| `get_db` |
| Config / Settings | 环境变量、数据库地址、密钥 | 散落在 `database.py` / `alembic.ini` |
| Migration | 数据库结构变更 | `alembic/` |
| Infrastructure | 连接池、缓存、队列、外部客户端 | `database.py` 的 `engine` |

### 6. MVC vs 分层架构

- **MVC**：Model / View / Controller，关注"数据、展示、请求处理"
- **分层架构**：Controller → Service → Repository → DB，关注"业务逻辑与数据库访问"

后端 Web 项目通常混用两个概念，但更常见的是按层拆。

项目变大后的典型结构：

```
app/
├── main.py              # 只创建 app、挂载 router
├── routers/             # Router 层
│   ├── users.py
│   └── todos.py         # Controller 函数
├── services/            # Service 层
├── repositories/        # Repository 层
├── models.py            # Model / Entity
├── schemas.py           # Schema / DTO
├── database.py          # 基础设施
├── dependencies.py      # get_db、get_current_user
└── config.py            # Settings
```

> 现阶段不拆：项目规模小，controller 直接操作 ORM 合理。等 controller 里塞了注册、登录、token 校验、缓存后再拆。

### 7. 这些分层在 roadmap 里的覆盖情况

| 概念 | 后续哪里会碰到 |
|------|---------------|
| Model / ORM | 学习项 6 ✅ |
| Schema / DTO | 学习项 0.6 ✅ + 本项目 |
| Migration | 学习项 7 ✅ |
| Dependency | 学习项 3 ✅、12 OAuth2 |
| Middleware | 学习项 3、14 CORS、27 日志、30 限流 |
| Config / Settings | 学习项 20 CI/CD、21 Docker（无专门项）|
| Infrastructure | 16 Redis、19 Nginx、21 Docker、22 Celery、24 索引、25 MongoDB |
| Router 拆分 | 第三阶段认证项目、第四阶段工程化项目（无专门项）|
| Service 层 | 注册/登录、缓存逻辑（无专门项）|
| Repository 层 | 学习项 17/18 测试与 mock 数据库（无专门项）|
| 架构取舍 | 学习项 23 单体 vs 微服务、32 System Design |

结论：约 6~7 成有正式学习项，3 成会在阶段项目里自然遇到。分层重构不必现在做，等第四阶段工程化项目开始时再做一次「`main.py` 拆 routers / services / repositories」的练习。
