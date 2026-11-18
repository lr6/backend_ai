# 阶段项目 · 工程化 Todo API — 学习笔记（Task 1）

> 完成日期：2026-11-18（Task 1A / 1B / 1C）
> 数据库：`eng_todo_db`（`alembic_version = aa893607ca00`）
> 项目目录：`4工程化/阶段项目-工程化TodoAPI/`
> 依赖：仓库根目录 `.venv`（fastapi / sqlalchemy / alembic / passlib / bcrypt / python-jose / python-multipart）

---

## 一、项目结构

```
main.py              组装 app：include_router + 全局路由（/users/me）
  │
  ├─→ routers/auth.py      /auth/register · /auth/login · /auth/refresh
  ├─→ routers/todos.py     /todos CRUD（每条都只操作自己的）
  │        │
  │        └─→ deps.py     get_current_user（从 Bearer token 认人）
  │
  ├─→ schemas.py           Pydantic 请求/响应模型
  ├─→ models.py            User（含 password_hash）/ Todo
  ├─→ security.py          纯函数：bcrypt + JWT
  └─→ database.py          engine / SessionLocal / Base / get_db
           │
           └─→ config.py   环境变量只在这一处读取

alembic/env.py ──→ config.DATABASE_URL + Base.metadata + models
```

依赖方向是单向的：

```
config.py（根，不 import 项目内任何模块）
   ↑
database.py / security.py
   ↑
models.py / schemas.py
   ↑
deps.py
   ↑
routers/*.py
   ↑
main.py
```

`database.py` **不 import models**（否则 models → database → models 循环引用），
`deps.py` 单独存在是为了让 `routers/todos.py` 不用 import `routers/auth.py` ——
否则 router 之间互相依赖，拆包就白拆了。

---

## 二、任务拆解

| Task | 内容 | 状态 |
|------|------|------|
| 1A | `config.py` + `database.py` —— 配置集中、连接 `eng_todo_db` | ✅ |
| 1B | `models.py` / `schemas.py` / `security.py` / Alembic 建表 | ✅ |
| 1C | `deps.py` + `routers/` + `main.py` 组装 | ✅ |
| 2 | Redis 缓存层 | ⬜ |
| 3 | pytest 测试体系 | ⬜ |
| 4 | Nginx 反向代理 | ⬜ |
| 5 | CI/CD | ⬜ |

---

## 三、知识点讲解

### Task 1A · config.py + database.py

**为什么单独一个 config.py？**

- 数据库地址、Redis 地址、密钥如果散落在各模块，换环境要翻遍代码；
- 第三阶段 `security.py` 里 `SECRET_KEY` 是硬编码的 —— 源码一旦进 Git 就是泄露；
- 同一份代码要能跑在 dev / test / prod，差异只应该来自环境变量。

```python
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg:///eng_todo_db")
REDIS_URL: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-secret-change-me")
```

- `os.getenv(名字, 默认值)`：环境变量优先，读不到用默认值；
- 默认值只给本地开发用，部署时环境里必须设置真实密钥；
- Redis URL 末尾的 `0` 是 db 编号（学习项 16 练习用 15，生产用 0），不同用途分不同 db 互不干扰。

**测试里为什么要 `importlib.reload`？**

模块只在第一次 `import` 时执行，之后改 `os.environ` 不会让已经读过的常量更新。
`importlib.reload(模块)` 会重新执行一遍模块代码 —— 模拟「进程用新环境变量重新启动」。

**database.py 的关键改动**：`DATABASE_URL` 不再写死，而是 `create_engine(config.DATABASE_URL)`。

### Task 1B · models / schemas / security / Alembic

**models.py**：users 表多一列 `password_hash: Mapped[str] = mapped_column(String(255))`

- 列名是 `password_hash` 不是 `password` —— 名字说明「存的是哈希」；
- `Mapped[str]`（非 `str | None`）→ 自动 NOT NULL；
- 长度 255 给算法迁移留余量（bcrypt 是 60 位，将来换 argon2 可能更长）。

**schemas.py**：

- `password: str = Field(min_length=8, max_length=72)`
  - 下限 8：太短在离线爆破面前等于没有；
  - 上限 72：bcrypt 只处理前 72 **字节**，超出部分会被静默截断；
- `UserRead` 里没有 `password_hash` —— 响应模型就是白名单；
- `TodoCreate` 删掉 `user_id` —— 身份从 token 来，客户端传了也不采信（防 IDOR）。

**security.py**：`SECRET_KEY = config.SECRET_KEY`，不再是硬编码。

**Alembic**：`env.py` 里三件事

1. `import config as app_config` + `import models`（不 import 模型，metadata 是空的）；
2. `target_metadata = Base.metadata`；
3. `context.config.set_main_option("sqlalchemy.url", app_config.DATABASE_URL)`。

### Task 1C · 拆包：deps / routers / main

**deps.py 的职责：认人。**

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def auth_error(detail: str = "invalid credentials") -> HTTPException:
    return HTTPException(401, detail, headers={"WWW-Authenticate": "Bearer"})
```

- `auth_error` **返回**一个异常对象，调用方再 `raise` —— 复用了「401 + WWW-Authenticate」的构造；
- `tokenUrl` 只影响 Swagger 的 Authorize 按钮，不影响真实请求。

```python
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        claims = security.decode_token(token, "access")   # refresh 不能访问业务接口
    except JWTError:
        raise auth_error("invalid token")
    user = db.get(models.User, claims["user_id"])
    if user is None:
        raise auth_error("invalid token")
    return user
```

**router 拆包**：路径只写相对部分，`prefix` 拼在前面。

```python
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", ...)      # 实际是 /auth/register
```

`main.py` 只做三件事：创建 app、挂路由、挂全局中间件（Task 2 才加）。
`include_router(A)` 传的是 **router 对象**，不是模块、也不是 `APIRouter` 类：

```python
app.include_router(auth.router)
app.include_router(todos.router)
```

**所有权 = 防 IDOR**：每条 todo 操作都同时按 `id` + `user_id` 查，
别人的资源统一 **404**（不是 403 —— 403 等于告诉对方「存在但你无权」）。

这段逻辑在三个路由里重复，Review 后抽成了私有函数：

```python
def _get_owned_todo(todo_id: int, current_user: models.User, db: Session) -> models.Todo:
    stmt = select(models.Todo).where(
        models.Todo.id == todo_id,
        models.Todo.user_id == current_user.id,
    )
    todo = db.scalar(stmt)          # 一条或 None
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="todo not found")
    return todo
```

放在 `routers/todos.py` 而不是 `deps.py`：它只服务 todo 的数据访问；
`deps.py` 放跨路由共享的依赖（如 `get_current_user`）。

**scalar vs scalars**：

| 方法 | 返回 | 用途 |
|------|------|------|
| `db.scalars(stmt)` | `ScalarResult`（一组，永远不是 None） | 列表 → `.all()` |
| `db.scalar(stmt)` | 一个模型对象 或 `None` | 单条 → 判 404 |

**PATCH 的部分更新**：

```python
data = payload.model_dump(exclude_unset=True)   # 只含客户端真的传了的字段
for key, val in data.items():                   # dict 直接 for 只给 key！
    setattr(todo, key, val)
db.commit()
db.refresh(todo)
```

`exclude_unset=True` 是为了区分「没传」和「传了 False / None」——
`if done:` 会把 `False` 当成没传。

**response_model 已经负责 ORM → dict 的转换**：`TodoRead` 有
`model_config = ConfigDict(from_attributes=True)`，路由里直接 `return todo` 即可，
不要手工 `schemas.TodoRead(id=todo.id, ...)` —— 加字段时会漏。

### 补充提问 1 · 已经声明 `response_model`，为什么还要 `return` 构造对象？

**提问原话**：「auth.py 里实现登录和刷新已经写了 `response_model=schemas.TokenPair`，
为啥还要 `return schemas.TokenPair(...)`，我不是很理解。」

`response_model` 不生产数据，它只做「出口检查 + 说明书」：

| 职责 | 说明 |
|------|------|
| OpenAPI 文档 | Swagger 的响应示例、字段类型从这里来 |
| 响应校验 | 返回的东西不符合 → `ResponseValidationError` |
| 字段白名单 | `UserRead` 没有 `password_hash`，多返回的字段会被过滤 |
| 序列化 + 默认值 | 转 JSON；`token_type` 这类默认值在校验时补上 |

最硬的证据：`get_todo` 返回 `ScalarResult` 时，`response_model=TodoRead` 就在，
但它没能把 `ScalarResult`「变」成 `TodoRead`，只会报
`ResponseValidationError: 'id': Field required, input: <ScalarResult>`。

**前端类比**：TypeScript 的返回类型标注不会替你创建对象，函数体还得 `return`：

```ts
function login(): TokenPair {
  return { accessToken, refreshToken }   // 标注只是合同
}
```

**为什么这里要构造**：两个 token 是两个函数调用现造的字符串，不像 `todo` 那样背后
有一个现成 ORM 对象（靠 `from_attributes` 自动读属性），所以必须装进某种结构。
两种写法等价：

```python
return schemas.TokenPair(access_token=..., refresh_token=...)   # Pydantic 实例：类型检查
return {"access_token": ..., "refresh_token": ...}              # dict：短，默认值由 response_model 补
```

最终采用 dict 写法，`token_type` 由 `TokenPair` 的默认值在校验时补上。
**要不要构造，取决于手里已经有什么，而不是 response_model 有没有声明。**

### 补充提问 2 · `=` 什么时候加空格？

**提问原话**：「是只有变量赋值才加吗，剩下的场景统统不加吗？」

准确说：**「绑定一个名字」加空格，「给参数起个名字」不加**。

| 场景 | 写法 | 空格 |
|------|------|------|
| 普通赋值 | `x = 1` | ✅ |
| 增强赋值 | `count += 1` | ✅ |
| 类型注解赋值 | `x: int = 1` | ✅ |
| 元组解包 | `a, b = 1, 2` | ✅ |
| 函数调用关键字参数 | `User(username="a")` | ❌ |
| 函数定义默认值（无注解） | `def f(x=1):` | ❌ |
| 函数定义默认值（**有注解**） | `def f(x: int = 1):` | ✅ |
| lambda 默认值 | `lambda x=1: x` | ❌ |

反直觉点：同样在 `def` 里，有没有类型注解决定了要不要加空格。

### 补充 · 并发注册的兜底（生产细节）

「先查重 → 再插入」是两步，两个并发请求可能同时通过查重、同时插入，
其中一个触发数据库唯一约束 → `IntegrityError` → 默认变成 500。

修法：让数据库约束做最终裁判，并接住异常：

```python
try:
    db.commit()
except IntegrityError:
    db.rollback()                  # 必须！失败事务不清掉，后续查询会 PendingRollbackError
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="username already taken",
    ) from None                    # 不把数据库原始错误栈暴露出去
```

`IntegrityError` 是笼统的（外键、非空、其他唯一约束都抛它）；这张表只有 username
一个唯一约束，所以可以放心当 409 处理。预检查留不留都行：留 = 常见情况走快路径，
不留 = 只剩数据库一条真理来源。

---

## 四、练习 ↔ 知识点映射

| Task | 检查点 | 对应知识点 |
|------|--------|-----------|
| 1A config.py | 环境变量优先 + 默认值 + reload | 配置集中、依赖树根 |
| 1A database.py | engine/SessionLocal/get_db、连接归还 | 生成器依赖、连接池 |
| 1B models.py | password_hash 非空 + String(255) | Mapped 类型注解决定可空性 |
| 1B schemas.py | 72 上限、UserRead 白名单、TodoCreate 无 user_id | Pydantic 约束、响应模型即白名单 |
| 1B Alembic | autogenerate 出两张表并 upgrade | 迁移=数据库的 Git |
| 1C deps.py | auth_error + get_current_user | 401 头、token 类型校验 |
| 1C auth.py | 注册 409 / 登录 form / 刷新 | OAuth2 password flow、双 token |
| 1C todos.py | 所有权 404、`db.scalar`、`exclude_unset` | IDOR 防御、ORM 查询 |
| 1C main.py | 全部 30 条端到端断言 | 分包组装 |

---

## 五、本次纠错全记录（Task 1C）

### 问题 1：`where(id == todo_id, user_id == current_user.id)`

- **现象**：`NameError: name 'user_id' is not defined`，通过 TestClient 冒出来；
- **原因**：
  - `user_id` 在当前作用域、全局、内置里都找不到 → NameError；
  - `id` 是 **Python 内置函数**（`id(obj)` 返回内存地址）→ 不报错，`id == todo_id` 静默为 `False`，SQL 变成 `WHERE false`；
  - 类属性不在名字查找链里，必须显式 `models.Todo.user_id`；
- **对应知识点**：名字解析 LEGB；Vue 里 `this.userId` vs 裸 `userId`；
- **解决**：所有列写成 `models.Todo.xxx`；
- **Claude 的锅**：练习 docstring 里的伪代码没带 `models.Todo.` 前缀，被照抄后直接踩坑。已修正提示文本。
- **顺带记**：`id / type / list / dict / all / any / sum / max / min / filter / next / input` 都是内置名字，裸用不报错但拿到的是内置对象。

### 问题 2：构造了语句却没存，`db.scalars(select)`

- **现象**：`ArgumentError: Executable SQL or text() construct expected, got <function select at 0x...>`；
- **原因**：`select(...)` 的结果被丢掉，`db.scalars(select)` 传入的是 `from sqlalchemy import select` 的函数对象；
- **对应知识点**：学习项 6「构造 ≠ 执行」；
- **解决**：`stmt = select(...)`，再 `db.scalar(stmt)`。

### 问题 3：`db.scalars` 当成单条查

- **现象**：`ResponseValidationError: missing id/title/done/user_id, input: <ScalarResult object>`；
  且 `if todo is None` 永远不成立；
- **原因**：`scalars` 返回结果集，不是模型对象，也不可能是 `None`；
- **解决**：单条查询用 `db.scalar(stmt)`。

### 问题 4：`for key, val in data:`（data 是 dict）

- **现象**：`ValueError: too many values to unpack (expected 2)`；
- **原因**：直接遍历 dict 拿到的是 key，`"done"` 是 4 个字符的字符串，塞不进两个变量；
- **对应知识点**：dict 遍历 `/ .items()`（学习项 9/10 同款错）；
- **解决**：`for key, val in data.items():`。

### 问题 5：`update_todo` 漏了 404 判断

- **现象**：`AttributeError: 'NoneType' object has no attribute 'done'`；
- **原因**：`db.scalar` 查别人的 todo 返回 None，接着 `setattr(None, "done", True)`；
- **解决**：`scalar` 之后统一

```python
if todo is None:
    raise HTTPException(404, "todo not found")
```

### 问题 6：`delete_todo` 也是 `scalars`

- **现象**：`UnmappedInstanceError: Class 'ScalarResult' is not mapped`；
- **原因**：`setattr` 能往任意对象挂属性所以没报，直到 `db.refresh()` 拿 `ScalarResult` 去问 SQLAlchemy「这是哪张表」才炸；
- **解决**：同样换 `db.scalar`。

### 问题 7：注册提示拼写错误（测试绿没发现）

- **现象**：`main.py` 全绿，但跑真实请求看到的响应是
  `{"detail": "useranme alerady taken"}`；
- **原因**：测试只断言 `r.status_code == 409`，没看 `detail` 的内容；
- **解决**：两处都改成 `"username already taken"`；
- **教训**：**测试绿 ≠ 无 bug**（第三次 —— 学习项 13 的 verify 返回值丢失、
  学习项 16 的哨兵被写成 `"null"`）。测试只覆盖它断言过的东西，
  用户可见的字符串要自己核对。

> **这一串错误的共同根**：以为「手里拿到的东西」和「实际拿到的东西」一样。
> 每次报错都先读最后一行异常类型 + 信息，它通常直接把答案写出来了（`got <function select>`、`input: <ScalarResult>`、`'NoneType'`）。

---

## 六、踩坑速查表

| 错误写法 | 报错 | 正确写法 |
|----------|------|----------|
| `.where(id == todo_id)` | 不报错，永远查不到（WHERE false） | `.where(models.Todo.id == todo_id)` |
| `.where(user_id == ...)` | `NameError: name 'user_id' is not defined` | `.where(models.Todo.user_id == ...)` |
| `select(...)` 不赋值，`db.scalars(select)` | `ArgumentError ... got <function select>` | `stmt = select(...)` → `db.scalar(stmt)` |
| 单条用 `db.scalars(stmt)` | `ResponseValidationError` / 永远不 404 | `db.scalar(stmt)` |
| `for k, v in data:`（data 是 dict） | `ValueError: too many values to unpack` | `for k, v in data.items():` |
| `setattr(None, ...)` | `AttributeError: 'NoneType' object has no attribute ...` | 先判 `if todo is None: raise 404` |
| `db.refresh(ScalarResult)` | `UnmappedInstanceError: ... not mapped` | 传模型对象 |
| 手工 `schemas.TodoRead(id=..., ...)` | 不漏但容易忘字段 | `return todo`（`from_attributes`） |
| 以为声明了 `response_model` 就不用产出数据 | 不报错，但逻辑错 / 500 | `response_model` 只校验和序列化，数据要自己 return |
| `db.commit()` 失败不 `rollback` | 后续查询 `PendingRollbackError` | `except IntegrityError: db.rollback()` |
| 用户可见字符串写错（`useranme`） | 测试绿但接口文案错 | 断言 `detail`；真实请求看响应 |

---

## 七、常用命令

```bash
# 均在仓库根目录 backend_ai 下执行
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/config.py"
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/database.py"
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/models.py"
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/schemas.py"
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/security.py"
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/main.py"      # Task 1C 端到端

# Alembic（在项目目录内）
cd "4工程化/阶段项目-工程化TodoAPI"
../../.venv/bin/alembic current
../../.venv/bin/alembic upgrade head
```
