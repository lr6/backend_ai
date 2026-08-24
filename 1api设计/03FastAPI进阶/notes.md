# 第一阶段 · 3 FastAPI 进阶 — 学习笔记

> 完成日期：2026-08-24
> 状态：✅ 3 个练习全通（一次通过，无踩坑）

---

## 一、知识点讲解

### 1. Depends（依赖注入）

**是什么**：路由函数声明「我需要某个东西」，FastAPI 自动调用对应的函数，把结果「注入」进来。**不用手动调用**那个函数。

```python
def get_current_user(x_username: str = Header(default="anonymous")):
    return x_username

@app.get("/me")
def me(user: str = Depends(get_current_user)):   # ← 自动注入
    return {"username": user}
```

`user` 的值不是前端传来的，而是 `get_current_user` 的返回值，由 FastAPI 自动算出来填进去。

**前端类比**：自定义 Hook。`useCurrentUser()` 封装「取当前用户」，组件里 `const user = useCurrentUser()` 直接拿结果。`Depends` 就是后端的自定义 Hook——逻辑写一次，处处复用。

**为什么有用**：真实项目里几乎每个接口都要「校验登录、连数据库」，没有依赖注入就得在几十个路由里复制粘贴；有了它，抽成依赖函数，`Depends(get_db)` 一行搞定。

### 2. 中间件（Middleware）

**是什么**：夹在「请求到达」和「响应返回」之间，对**所有**请求统一处理。

```python
@app.middleware("http")
async def add_process_time(request, call_next):
    start = time.time()                    # ① 请求前
    response = await call_next(request)    # ② 放行，走到路由
    process_time = time.time() - start     # ③ 响应后
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

**前端类比**：axios 拦截器。请求拦截器（发前加 token）、响应拦截器（收后处理错误）。中间件就是后端的拦截器。

**关键**：`await call_next(request)` 是分界线——前面的代码是「请求前处理」，后面是「响应后处理」。这行**必须写**，没有它请求就卡死走不到路由。

### 3. 生命周期（Lifespan）

**是什么**：应用**启动时**执行一次（连数据库），**关闭时**执行一次（断数据库）。

```python
@asynccontextmanager
async def lifespan(app):
    lifecycle_events.append("startup")   # 启动时
    yield                                 # ← 正常运行期间
    lifecycle_events.append("shutdown")  # 关闭时

app = FastAPI(lifespan=lifespan)
```

**前端类比**：React 的 useEffect 挂载/卸载。`yield` 之前 = `componentDidMount`，之后 = `componentWillUnmount`。

**关键**：`yield` 是分界线——之前「启动」，之后「关闭」。

---

## 二、练习 ↔ 知识点映射

| 练习 | 知识点 | 关键 API/语法 |
|------|--------|--------------|
| 1 Depends | 依赖注入复用逻辑 | `Depends(get_current_user)`、`Header(default=...)` |
| 2 中间件 | 请求/响应统一处理 | `@app.middleware("http")`、`await call_next(request)` |
| 3 生命周期 | 启动/关闭钩子 | `@asynccontextmanager`、`yield` |

---

## 三、附带知识点（本次没有踩坑，但值得记住）

1. **`Header` 参数名自动转请求头**：`x_username` → 请求头 `X-Username`（下划线转连字符，首字母大写）。所以测试里 `headers={"X-Username": "zhibo"}` 能命中参数 `x_username`。
2. **HTTP 头的值必须是字符串**：`time.time()` 返回 float，写进 `response.headers` 前要 `str()`。
3. **`with TestClient(app)` 触发完整生命周期**：进入 `with` 触发 startup，退出触发 shutdown。不用 `with` 时，第一次请求会触发 startup，但 shutdown 不会触发。
4. **lifespan 必须先定义**：创建 `FastAPI(lifespan=lifespan)` 时就要把函数传进去，所以 lifespan 函数体在 `app = FastAPI(...)` 之前。

---

## 四、易错点速查表（本次没踩，作为预防）

| 易错点 | 后果 | 正确做法 |
|--------|------|---------|
| 中间件忘写 `await call_next(request)` | 请求卡死，永远到不了路由 | 必须 `response = await call_next(request)` |
| lifespan 里忘写 `yield` | `asynccontextmanager` 报错 | `yield` 是必须的分界线 |
| 头值直接写 float | 报类型错误 | `str(process_time)` |
| lifespan 定义在 `FastAPI()` 之后 | 构造时传不进去 | lifespan 在 `app = FastAPI(lifespan=...)` 之前定义 |
| `Header` 参数名写错大小写 | 取不到值 | 参数用下划线 `x_username`，FastAPI 自动转 `X-Username` |
