# 第一阶段 · 4 自动文档 — 学习笔记

> 完成日期：2026-08-24
> 状态：✅ 4 个练习全通

---

## 一、知识点讲解

### 1. FastAPI 自动生成两种文档

写完 FastAPI 应用后，默认自动多出两个地址：

| 地址 | 是什么 | 给谁看 |
|------|--------|--------|
| `/docs` | Swagger UI，交互式网页 | 给人看 |
| `/openapi.json` | OpenAPI 规范，机器可读 JSON | 给程序看 |

**前端类比**：
- `/docs` 的 Swagger UI ≈ 自动生成的 Postman / Apifox，所有接口自动列出，点「Try it out」在线调试。
- `/openapi.json` ≈ 接口的「JSON 契约」，类似 `.d.ts` 类型定义文件。

Swagger UI 不是单独写的——它就是根据 `/openapi.json` 渲染出来的。核心是那一个 JSON。

### 2. 文档从代码里「提取」

| 你的代码 | 出现在文档哪里 |
|---------|--------------|
| 路由 `@app.get("/hello")` | `paths` 里的 `/hello` |
| Pydantic 模型 `Todo` | `components.schemas` 里的 `Todo` |
| 参数类型注解 `x: int` | 参数的 type |
| docstring / summary | 接口描述 |

**文档永远不过时的原因**：改代码，文档自动跟着变。手写文档最大的问题是「代码改了文档忘了改」。

### 3. 前端怎么用这个 JSON（全栈最实在的价值）

前端拿到 `/openapi.json`，用工具自动生成：
- **TypeScript 类型定义**（`openapi-typescript`）—— 后端 Pydantic 模型变前端 `interface Todo`，类型永不脱节
- **API 调用函数**（`openapi-generator`）—— 自动生成 `fetchTodo()` 等封装

**前端类比**：手动写 `interface Todo` + `fetch('/todos')`，接口一改就崩。基于 OpenAPI 生成，后端改字段 → 前端重新生成 → 编译器直接报错告诉哪里对不上。

### 4. 自定义文档信息

```python
app = FastAPI(
    title="Todo API",
    description="一个待办事项管理接口",
    version="1.0.0",
)
```
显示在 Swagger UI 顶部，也写进 `openapi.json` 的 `info` 字段。

### 5. ⭐ 模型要被路由引用才进文档

OpenAPI **只收录被路由引用到的模型**。光 `class Todo(BaseModel)` 定义，没路由用它当请求体/响应模型，它不会进 `components.schemas`。

**前端类比**：tree-shaking——`import` 了但没用到的模块，打包时被摇掉。FastAPI 文档也只登记「接口真正用到的」模型。

---

## 二、练习 ↔ 知识点映射

| 练习 | 知识点 | 关键 API |
|------|--------|---------|
| 1 自定义文档信息 | `info` 字段 | `FastAPI(title, description, version)` |
| 2 模型进 schemas | 模型要被路由引用 | `def f(todo: Todo)` 请求体 |
| 3 路由进 paths | 路由自动登记 | `@app.get("/hello")` |
| 4 Swagger UI | `/docs` 可访问 | 自动生成 |

---

## 三、练习纠错全记录

### 练习 1：缺逗号 + 拼写错误（改 1 次）

**第 1 版（错）**：
```python
app = FastAPI(
    titlle='Todo API'          # ❌ 缺逗号 + 拼错 title
    description='一个待办事项管理接口'
    version='1.0.0'
)
```
- **现象 1**：`SyntaxError: invalid syntax. Perhaps you forgot a comma?`（Python 直接提示忘了逗号）
- **原因 1**：函数传多个参数，参数之间必须用逗号隔开
- **现象 2**：加完逗号后 `TypeError: unexpected keyword argument 'titlle'`
- **原因 2**：`title` 拼成了 `titlle`（三个 l）
- **知识点**：JS 拼错属性名静默 `undefined`，Python 关键字参数拼错直接报错——Python 反而「拼错就炸」，帮你早发现

### 练习 2：模型没被路由引用（题目疏漏 + 补一个路由）

- **现象**：`Todo` 没出现在 `components.schemas`，三个测试全挂
- **原因**：光定义 `class Todo(BaseModel)`，没有路由用它当请求体/响应模型，FastAPI 就不会登记它
- **知识点**：OpenAPI 只收录「被路由引用」的模型（tree-shaking 类比）
- **解决**：加一个使用 Todo 的路由
```python
@app.post("/todos")
def create_todo(todo: Todo):
    return todo
```

---

## 四、踩坑速查表

| 错误写法 | 报错/现象 | 正确写法 | 知识点 |
|----------|----------|---------|--------|
| `FastAPI(a=1 b=2 c=3)` 参数无逗号 | `SyntaxError: forgot a comma` | `FastAPI(a=1, b=2, c=3)` | 参数用逗号隔开 |
| `title` 拼成 `titlle` | `TypeError: unexpected keyword argument` | `title="..."` | 关键字参数拼错直接报错 |
| 只 `class Todo(BaseModel)` 定义不用 | Todo 不在 schemas | 加路由 `def f(todo: Todo)` | 模型要被路由引用才进文档 |
