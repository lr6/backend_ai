# 0.3 类型提示 (Type Hints) — 学习笔记

## 核心概念

Python Type Hints ≈ **TypeScript 类型标注**，但有一个关键区别：

| | TypeScript | Python Type Hints |
|---|---|---|
| **检查时机** | 编译时报错 | 运行时**不检查**，只是给 IDE/mypy 看 |
| **工具** | tsc | mypy / pyright / PyCharm |
| **是否阻止运行** | 是 | 否 |

## 速查表

| 你想标注... | 写法 |
|------------|------|
| 字符串 | `str` |
| 整数 | `int` |
| 浮点数 | `float` |
| 布尔值 | `bool` |
| 可能为空 | `str \| None` |
| 字符串列表 | `list[str]` |
| 字典（K→V） | `dict[str, int]` |
| 固定元组 | `tuple[str, int]` |
| 函数类型 | `Callable[[入参类型], 返回值类型]` |
| 复杂类型起名 | `Alias = list[dict[str, int]]` |
| 字典结构 | `class MyDict(TypedDict):` |

## JS/TS 对照

| TypeScript | Python |
|------------|--------|
| `string \| null` | `str \| None` |
| `Array<number>` | `list[int]` |
| `Record<string, number>` | `dict[str, int]` |
| `[string, number]` | `tuple[str, int]` |
| `type UserID = number` | `UserID = int` |
| `interface User { name: string }` | `class User(TypedDict):` |
| `(x: number) => boolean` | `Callable[[int], bool]` |

## 关键语法

```python
# 函数签名（最常用）
def foo(name: str, age: int) -> str:
    return f"{name} is {age}"

# Optional — 后端最常见：查数据库可能返回 None
def find_user(uid: int) -> dict | None:
    ...

# 容器泛型（Python 3.9+）
scores: list[int] = [90, 85]
config: dict[str, str | int] = {"port": 8000}
point: tuple[float, float] = (116.4, 39.9)

# TypedDict — FastAPI 里大量使用
class TodoItem(TypedDict):
    title: str
    done: bool
    priority: int

# 类型别名
UserID = int
UserInfo = dict[str, str | int | None]
```

## 旧式写法（认识即可，不推荐新代码使用）

```python
from typing import Optional, Union, List, Dict, Tuple

# 旧                      # 新（3.9+）
Optional[str]              str | None
Union[int, str]            int | str
List[int]                  list[int]
Dict[str, int]             dict[str, int]
Tuple[int, str]            tuple[int, str]
```

## 踩坑记录

- `round()` 用于保留小数位数：`round(91.666..., 2)` → `91.67`
- `dict.get(key)` 找不到时返回 `None`，天然契合 `| None` 返回类型
- TypedDict 定义时类体里写的是**类型**，不是默认值

---

## Q&A：类型标注到底有没有用？

### Q1：Python 是弱类型/动态类型，类型标注运行时不检查，写它干嘛？

首先纠正：Python 不是弱类型，是**动态强类型**。`"1" + 1` 在 JS 里返回 `"11"`，在 Python 里直接 `TypeError`。

类型标注的实际价值在三个地方：

**① IDE 智能提示 — 最直观**

```python
# 没标注：IDE 不知道 data 是啥，点号后面不提示
def process(data):
    return data.  # ← 无提示

# 有标注：IDE 弹出 .get() .keys() .items()
def process(data: dict[str, int]) -> str:
    return data.  # ← 自动补全
```

**② 重构安全 — 类似 TS 的「改了类型，编译器告诉你哪里坏了」**

```python
class User(TypedDict):
    name: str
    email: str

def send_email(user: User) -> None:
    print(user["emial"])  # ← mypy 直接报错：TypedDict 没有 "emial" 这个 key
```

**③ FastAPI 的核心机制 — 类型标注驱动框架**

FastAPI 用类型标注做三件事：请求体自动校验、自动生成 Swagger 文档、IDE 自动补全。你写了类型，框架帮你干活。

### Q2：Python 类型标注是可选的吗？和 TS 的区别？

**是的，Python 是渐进式类型（Gradual Typing）。**

同一个文件里三种写法可以共存，运行完全不报错：

```python
def add(a: int, b: int) -> int:      # 全标注
    return a + b

def subtract(a, b):                   # 零标注
    return a - b

def multiply(a: int, b):             # 半标半不标
    return a * b
```

TS 做不到——`.ts` 文件只要开了 `strict`，不写类型就报错。

**根源**：Python 的类型标注只是挂在函数 `__annotations__` 属性上的元数据，解释器运行时不看。

```python
def foo(x: int) -> str:
    return str(x)

print(foo.__annotations__)
# {'x': <class 'int'>, 'return': <class 'str'>}
```

### 实际项目策略

| 场景 | 是否标注 |
|------|---------|
| **公开 API（FastAPI 路由）** | 必须写，框架靠它干活 |
| **内部工具函数** | 写了有 IDE 提示，可选 |
| **原型/脚本** | 不写，快速验证 |

### TypeScript vs Python Type Hints 总结

| | TypeScript | Python Type Hints |
|---|---|---|
| **无类型语言** | JavaScript | Python |
| **检查工具** | `tsc` 编译器 | `mypy` / `pyright` / IDE |
| **检查时机** | 编译时 | 编码时 / CI |
| **阻止运行** | 是（不编译跑不了） | 否（类型错了照样跑） |
| **覆盖策略** | 全量（选了 TS 就得写） | 渐进式（想标就标） |
| **类型存储** | 编译产物 | `__annotations__` 属性 |
| **核心哲学** | 让代码**不能**跑直到类型正确 | 让代码**更好写** + **更早发现 bug** + **框架自动干活** |
