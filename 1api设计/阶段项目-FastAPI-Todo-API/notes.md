# 阶段项目：FastAPI Todo API — 学习笔记

> 第一阶段 · 阶段项目（综合大考）
> 完成日期：2026-08-24
> 状态：✅ 18 个测试全通（经过三轮纠错）

---

## 一、项目规划

### 目标

用 FastAPI 写一个完整的 Todo API（CRUD + 数据存内存），串起第一阶段全部知识。

### 5 个接口

| 方法 | 路径 | 成功状态码 | 说明 |
|------|------|-----------|------|
| GET | `/todos` | 200 | 分页列表 `{items, page, size, total}` |
| GET | `/todos/{id}` | 200 | 单个，404 |
| POST | `/todos` | 201 | 创建，自动生成 id |
| PUT | `/todos/{id}` | 200 | 更新，404 |
| DELETE | `/todos/{id}` | 204 | 删除，404 |

### 知识点 → 用途映射

| 学过的知识点 | 落地位置 |
|-------------|---------|
| 1 FastAPI 入门 | 路由、路径/查询参数、请求体 |
| 2 REST 设计 | 资源建模、状态码、分页、错误处理 |
| 3 FastAPI 进阶 | （本项目未用到 Depends/中间件，用 FastAPI 元信息） |
| 4 自动文档 | `FastAPI(title, description, version)` |

---

## 二、核心知识点讲解（本项目新学到的）

### 1. 请求体模型 ≠ 存储结构（⭐ 最重要）

`id` 是后端生成的，不该出现在请求体模型里。分清楚两样东西：

| 概念 | 字段 | 谁产生 |
|------|------|--------|
| 请求体模型 `Todo` | `title`、`done` | 客户端传（前端表单） |
| 存储结构（`todos` 里的 dict） | `id`、`title`、`done` | `id` 后端 `new_id` 追加 |

**前端类比**：数据库的 `AUTO_INCREMENT` 主键，`INSERT` 时从来不写 id。前端表单也不会有「id」输入框。

### 2. 路径参数默认是字符串

FastAPI 路径参数 `/todos/{todo_id}`，**不加类型注解默认 `str`**。加 `: int` 才会自动 `parseInt`。

```python
def get_todo(todo_id: int):   # "1" → int 1 ✅
def delete_todo(todo_id):      # "1" 还是 str，1 == "1" → False ❌
```

**前端类比**：URL 里一切天然是字符串，FastAPI 靠类型注解做类型转换。

### 3. 204 无内容

`status_code=204` + `return None`（或空），状态码在装饰器设，body 返回空。

---

## 三、纠错全记录（三轮，完整轨迹）

### 第一轮：JS 思维混入 Python（10 个问题）

用户第一次写完，把大量 JS 写法直接搬进 Python。分三类：

**A 类 · JS 写法（3 个，核心思维问题）**

| 错误写法 | 语言 | 正确写法 |
|---------|------|---------|
| `todos.splice(index, 1)` | JS `Array.splice` | `del todos[index]` / `todos.pop(index)` |
| `for t, index in enumerate(...)` | 解包顺序反 | `for index, t in enumerate(...)` |
| `new_id = if 1 len(...) == 0 else ...` | 三元乱序 | `1 if len(...) == 0 else ...` |

- `enumerate(list)` 返回 `(下标, 元素)`，与 JS `forEach((item, index))` 顺序**相反**
- Python 三元是 `值A if 条件 else 值B`，JS 是 `条件 ? A : B`

**B 类 · 路由参数设计（4 个）**

| 错误 | 正确 |
|------|------|
| `get_todos(q: str = None)` + `q.page` | `get_todos(page: int = 1, size: int = 10)` |
| `@app.post('todos')` 缺斜杠 | `@app.post('/todos')` |
| PUT `def update_todo(todo_id)` 缺请求体 | `def update_todo(todo_id: int, todo: Todo)` |
| DELETE 函数名重复 `update_todo` | `delete_todo` |

**C 类 · CRUD 逻辑（3 个）**
- POST 没存 `done`、没返回 `id`
- PUT 硬编码 `t['done'] = True`，没读请求体
- DELETE 删了没 `return`，循环后仍 `raise 404`

### 第二轮：请求体模型塞了 id（1 个核心 bug）

**现象**：`POST 422`，后续 `total=0`、`GET 404`、`DELETE 404` 全连锁失败。

**原因**：`Todo` 模型写了 `id: int`（必填），但 POST 请求体 `{"title": ...}` 没传 id，Pydantic 校验失败（422），`create_todo` 根本没执行。

**知识点**：请求体模型 ≠ 存储结构（见上）。`id` 是后端生成的，删掉模型里的 `id`。

**解决**：
```python
class Todo(BaseModel):
    title: str
    done: bool = False
```

### 第三轮：DELETE 路径参数缺 `: int`（1 个）

**现象**：`DELETE 204` 实际 404，`DELETE 后再查` 实际 200（没删掉）。

**原因**：`def delete_todo(todo_id)` 缺 `: int`，`todo_id` 是 `"1"`（str），`t['id'] == todo_id` 即 `1 == "1"` 永远 False。

**知识点**：路径参数默认 str，加 `: int` 才自动转换。

**解决**：`def delete_todo(todo_id: int)`。

---

## 四、踩坑速查表

| 错误写法 | 报错/现象 | 正确写法 | 知识点 |
|----------|----------|---------|--------|
| `todos.splice(i, 1)` | 无 splice 方法 | `del todos[i]` | Python 无 splice |
| `for t, index in enumerate(x)` | index 拿到的是元素 | `for index, t in enumerate(x)` | enumerate 返回 (下标, 元素) |
| `if 1 len(x) == 0 else` | SyntaxError | `1 if len(x) == 0 else ...` | 三元 `A if 条件 else B` |
| `Todo` 模型写 `id: int` | POST/PUT 422 | 模型去掉 id，id 后端生成 | 请求体模型 ≠ 存储结构 |
| `def f(todo_id)` 无 `: int` | 1 == "1" 永远 False | `def f(todo_id: int)` | 路径参数默认 str |
| `return {'code': 204}` | 状态码还是 200 | `status_code=204` + `return None` | 状态码 ≠ body |

---

## 五、项目总结

### 核心收获

1. **JS → Python 的思维切换是最大挑战**：`splice`/`enumerate`/三元表达式，都是前端习惯的惯性。写 Python 时要有意识地「查一下这个写法 Python 里叫什么」。
2. **请求体模型 ≠ 存储结构**：后端生成的数据（id）不该放进客户端传入的模型。这是「前端表单能填什么」vs「后端存了什么」的边界。
3. **类型注解的两种作用**：路径参数加 `: int` 不只是「提示」，而是让 FastAPI 真的做类型转换（`"1"` → `1`）。
4. **完整的 CRUD 已经成型**：这个内存 Todo API 就是第二阶段接 PostgreSQL 的蓝本——到时候把「内存 list」换成「数据库表」，接口逻辑几乎不变。

### 下一步衔接

第二阶段「数据持久化」：把这个 Todo API 的 `todos = []` 换成 PostgreSQL + SQLAlchemy，`id` 让数据库自增，`enumerate` 查找换成 SQL 查询。
