# 18 httpx + pytest — API 集成测试 学习笔记

> 状态：✅ 已完成（练习 1–10，12 个测试全部通过，2026-11-14 归档）
> 环境：pytest 9.2.0、httpx 0.28.1、FastAPI 0.141.1
> 运行：`.venv/bin/python -m pytest 4工程化/18httpx-pytest/ -v`

---

## 一、知识点讲解

### 1. TestClient 的本质：进程内调用 ASGI 应用

```
普通 httpx：  client → TCP socket → uvicorn → ASGI app
TestClient：  client → 直接调用 ASGI app（进程内函数调用）
```

- `TestClient` 建立在 **httpx** 之上，传输层是 **ASGI transport**
- **不需要启动 uvicorn、不占端口、没有真实网络**
- 但路由匹配、Pydantic 校验、依赖注入、中间件、异常处理、响应序列化**全是真的**

定位：**集成测试**——测「请求进来 → 整个应用 → 响应出去」的链路，只省掉网络层。

前端类比：用 `@vue/test-utils` + jsdom 跑组件测试，组件/事件/渲染是真的，但没有真浏览器。

异步应用的等价写法（进阶）：

```python
import httpx

transport = httpx.ASGITransport(app=app)
async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
    ...
```

### 2. 请求与响应 API

```python
r = client.get("/todos")
r = client.post("/todos", json={"title": "buy milk"})
r = client.get("/me", headers={"X-Token": "secret"})
```

| 写法 | 用途 | Content-Type |
|---|---|---|
| `json={...}` | JSON 请求体 | `application/json` |
| `data={...}` | 表单（登录接口 `OAuth2PasswordRequestForm`） | `application/x-www-form-urlencoded` |
| `headers={...}` | 认证头、自定义头 | — |
| `params={...}` | 查询参数 | — |

`client.post` 除 `url` 外**全是 keyword-only**，第二个位置参数不存在：

```python
client.post("/todos", {"title": "x"})        # ❌ TypeError: takes 1 positional argument
client.post("/todos", json={"title": "x"})   # ✅
```

响应：

| 属性 | 说明 |
|---|---|
| `r.status_code` | 状态码 |
| `r.json()` | 解析 JSON（无 body 时会抛错） |
| `r.content` | 原始字节 |
| `r.headers` | 响应头 |

**先断状态码，再断 body**：状态码错时 body 往往是错误信息，先断更容易定位。

**204 No Content 没有 body**：`r.json()` 会抛 `json.JSONDecodeError`；只断状态码，需要时断 `r.content == b""`。

### 3. 依赖覆盖：app.dependency_overrides

```python
app.dependency_overrides[get_store] = lambda: store
```

- FastAPI 解析 `Depends(get_store)` 时**先查这个字典**，命中就用替换函数
- 生产路由、`Depends` 代码一行不用改
- **key 必须是依赖函数对象本身**，字符串 `"get_db"` 不生效且不报错
- **value 必须是可调用对象**；直接给实例会报 `'Store' object is not callable`
- **`app` 是模块级单例**，override 是全局状态：fixture 的 `yield` 后必须 `clear()`
- 清理不能写 `app.dependency_overrides[key] = None`——key 还在，FastAPI 会去调用 `None`

### 4. 测试数据隔离（三层）

| 层 | 做法 | 解决 |
|---|---|---|
| 依赖覆盖 | `dependency_overrides[get_db] = override` | 路由用测试 Session，不碰生产 Session |
| 独立测试库 | 单独的 `*_test_db` / 内存 Store | 不碰开发数据；CI 可起空库 |
| 每测试干净 | 每测试新 Store；或建表 + 每测试 rollback | 测试间不污染、顺序无关 |

真实数据库的 fixture 结构：

```python
@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture
def db_session(engine):
    with Session(engine) as session:
        yield session
        session.rollback()
```

**scope 隔离的是对象，不是数据**：`commit()` 过的数据换新 Session 仍在；要清数据靠 teardown 的 `DELETE`/`TRUNCATE` 或「只 flush 不 commit」。

### 5. 测试文件组织

```
4工程化/18httpx-pytest/
├── app.py          # 被测应用
├── conftest.py     # store / client / db_session 等共享 fixture
└── test_api.py     # 测试用例
```

- fixture 放 `conftest.py`，测试文件免 import
- `client` fixture 依赖 `store` fixture，形成依赖链
- 带 `with TestClient(app) as client:` 会触发 lifespan 启动/关闭；没用 lifespan 可省略

### 6. 422 vs 401

| 状态码 | 触发点 | 含义 |
|---|---|---|
| 422 | FastAPI 验证层 | 请求格式不对：缺字段、类型错、**必填请求头缺失** |
| 401 | 业务/依赖函数 | 身份认证失败：没登录、token 无效 |

`x_token: str = Header(...)` 是必填头，缺失时请求进不到依赖函数，直接 422。
认证依赖应写成可选 + 主动抛 401：

```python
def require_token(x_token: str | None = Header(default=None)) -> str:
    if x_token != "secret":
        raise HTTPException(401, "invalid token")
    return "demo-user"
```

### 7. getattr 语义（前端 `obj[name]` 的对应物）

```python
getattr(obj, name, default)   # 取属性；第三个参数是「找不到时的兜底值」
```

- `getattr` **从不调用**任何东西，只取属性
- `getattr(client, method)` 返回方法对象
- `getattr(client, method)(url)` 取到方法后再调用
- `getattr(client, method, url)` 是「取 method，找不到就返回 url」，第三个参数**不会**传给方法

前端对应：

```js
client[method]            // 取函数
client[method]("/todos")  // 取函数再调用
```

### 8. 「测试通过 ≠ 行为正确」

练习 7 出现过经典假阳性：DELETE 路径写成 `/todo/1`（少了 s），路由不存在 → 404。
最后一步 `GET /todo/1` 断言 404 也通过了，但原因是**路由不存在**，不是资源被删。即使删除逻辑完全没实现，测试照样绿。

排查方法：断言 404 时确认 URL 是**正确路由**；可以再加一条「删除前 GET 是 200」的断言锁定语义。

---

## 二、练习 ↔ 知识点映射

| 练习 | 内容 | 对应知识点 |
|---|---|---|
| 1 | `store` fixture | 每个测试一套干净数据 |
| 2 | `client` fixture | TestClient、dependency_overrides、teardown clear |
| 3 | GET 空列表 | 200、`r.json()` |
| 4 | POST 创建 | 201、`json=`、响应字段 |
| 5 | 空 title | 422（Pydantic 校验） |
| 6 | 不存在的资源 | 404 |
| 7 | DELETE | 204、`r.content == b""`、断言语义 |
| 8 | 测试隔离 | fixture 每测试独立 |
| 9 | 请求头认证 | 401 vs 422、`headers=` |
| 10 | parametrize 状态码 | `getattr(client, method)(url)` |

---

## 三、练习纠错全记录

### 探底 — 两题全不会

- TestClient 是否经过网络 → 不知道
- 真实数据库直接跑测试的问题 → 不知道

直接讲解：TestClient = 进程内 ASGI 调用；真库问题（慢、污染、顺序相关、危险、CI 跑不了、并行冲突）。

### 练习 1 — 类 vs 实例

```python
return Store      # ❌ 返回类本身
return Store()    # ✅ 实例
```

前端类比：拿到组件定义 vs `new` 出来的对象。

### 练习 2 — 两处

```python
app.dependency_overrides[get_store] = store           # ❌ 实例不可调用
app.dependency_overrides[get_store] = lambda: store   # ✅

app.dependency_overrides[get_store] = None            # ❌ key 残留，FastAPI 会调用 None
app.dependency_overrides.clear()                      # ✅
```

### 练习 3 — 拼写 + 括号

第一轮 `r.josn == []`：拼写错误（j-o-s-n vs j-s-o-n）+ 少括号。
第二轮 `r.josn()`：括号加了，拼写仍然反着。
**用户主动提问**：「getattr 的第三个参数不是传给方法的参数 看不懂」→ 用可运行 demo 演示了四种 getattr 返回值。

### 练习 4 — keyword-only 参数

```python
client.post('/todos', {"title": "buy milk"})          # ❌ TypeError
client.post("/todos", json={"title": "buy milk"})     # ✅
```

httpx 不猜请求体类型，`json=` / `data=` / `content=` 必须显式写。

### 练习 5、6 — 一次通过

### 练习 7 — 漏步骤 + 两处路径错误

第一轮：POST 后断言 204（应为 201），DELETE 整步缺失，GET 路径 `/todo/1`。
第二轮：DELETE 路径仍 `/todo/1`（少了 s），DELETE 返回 404。
第三轮通过。

**重点发现**：第三段 `GET /todo/1` 断言 404 会「假通过」——404 来自路由不存在，而不是资源被删。测试通过 ≠ 行为正确。

### 练习 8、9 — 练习 9 期望值受 Claude 出题错误影响

Claude 把 `x_token` 写成 `Header(...)`（必填），缺头时 FastAPI 返回 **422**，而练习要求断言 **401**。
Claude 修正 `app.py`（改为可选头 + 主动抛 401）后，用户按旧报错把断言改成 422，又需要改回 401。

### 练习 10 — getattr 两次用错

```python
getattr(method, url)                    # ❌ 从字符串 "get" 上找 "/todos"
getattr(client, method, url)            # ❌ 第三个参数是默认值，不是调用参数
getattr(client, method)(url)            # ✅
```

用可运行 demo 展示 `getattr(c, "get", "/x")` 第三个参数被无视、`getattr(c, "get")("/todos")` 才调用。

### Review 收尾

- 练习 4 的 `r.json()` 调用三次 → 存 `body = r.json()` 复用
- 单双引号统一、关键字参数两侧空格、`r.content == b""` 空格
- 段注释与函数间补足 2 空行
- 练习 8 补状态码断言

---

## 四、踩坑速查表

| 错误写法 / 现象 | 报错或后果 | 正确写法 |
|---|---|---|
| `return Store` | 得到类不是实例，`store.create()` 缺 self | `return Store()` |
| override 值给实例 | `'Store' object is not callable` | `lambda: store` / `def override(): return store` |
| override key 写字符串 | 不报错，覆盖不生效 | key 用 `get_store` 函数对象 |
| 清理写 `= None` | 下次请求 `NoneType object is not callable` | `app.dependency_overrides.clear()` |
| `client.post(url, {...})` | `TypeError: takes 1 positional argument` | `json={...}` |
| 表单接口用了 json= | 422 | `data={...}` |
| `r.josn()` | `AttributeError` | `r.json()` |
| 204 响应调 `r.json()` | `json.JSONDecodeError` | 只断状态码 / `r.content == b""` |
| 断言 404 但 URL 写错 | 假阳性，测试绿但没验证行为 | 确认路由正确，并先断删除前 200 |
| 必填 `Header(...)` 缺头 | 422 而非 401 | 认证头用可选 + 主动 `HTTPException(401)` |
| `getattr(obj, name, arg)` | 第三参数是默认值，不是调用参数 | `getattr(obj, name)(arg)` |
| 共享 `_store` 不覆盖 | 测试互相污染、顺序相关 | override 到每测试新建的 store |

---

## 五、与上一项（17 pytest）的衔接

- fixture 的 `yield` / 依赖 / conftest 机制直接复用到 API 测试
- parametrize 用于状态码矩阵
- 区别：17 测函数（单元），18 测整条 HTTP 链路（集成）；mock 的目标也从「模块函数」变成「依赖注入」

---

## 六、本章一句话总结

**TestClient 在进程内跑完整 ASGI 应用，`dependency_overrides` 把数据库依赖换成测试实例，fixture 负责每次干净的数据与清理；断言先状态码后 body，404 要确认路由正确——测试通过不等于行为正确。**
