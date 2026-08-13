# 0.5 异步基础 — 学习笔记

> 本笔记分两部分：**① 核心知识点讲解**（Claude 输出的知识）+ **② 练习纠错全记录**（本次会话的交流过程）。

---

## 一、核心知识点讲解

### 前端类比表

| 概念 | JavaScript | Python |
|------|------------|--------|
| 定义协程 | `async function f() {}` | `async def f():` |
| 等待结果 | `await promise` | `await coroutine` |
| 协程对象 | `Promise` | coroutine 对象 |
| 并发执行 | `Promise.all([...])` | `asyncio.gather(...)` |
| 异步等待 | `setTimeout(ms)` | `asyncio.sleep(秒)` |
| 后台任务 | （无直接对应） | `asyncio.create_task()` |

### 三个关键差异（JS → Python）

**1. 调用 `async def` 不执行，只返回协程对象**

```python
async def greet():
    return "hi"

coro = greet()      # 没执行！拿到一个 coroutine 对象
print(coro)         # <coroutine object greet ...>
asyncio.run(coro)   # 这才真正执行，返回 "hi"
```

JS 里调用 async 函数会立即返回 Promise；Python 里调用 async def 只是拿到一个「还没跑的任务描述」。

**2. 需要显式启动事件循环**

JS 的 event loop 由浏览器 / Node 自动管理。Python 要用 `asyncio.run()` 显式启动，且**只在最外层调用一次**。

**3. `gather` 吃的是可变参数，不是数组**

```python
# JS: 吃数组
Promise.all([p1, p2, p3])

# Python: 吃多个位置参数，list 要用 * 展开
asyncio.gather(c1, c2, c3)
asyncio.gather(*[c1, c2, c3])   # list 必须加 *
```

### 核心概念：`asyncio.run` vs `await`

| 你的位置 | 怎么执行协程 |
|---------|-------------|
| 最外层同步代码 | `asyncio.run(coro)` |
| `async def` 内部 | `await coro` |

`asyncio.run(coro)` 内部做了三件事：**新建事件循环 → 跑完协程 → 关闭循环**。

所以它有两个性质：
- 它是「启动按钮 / 冷启动」，只能调用一次
- 一个线程同一时刻只能有一个运行中的事件循环
- 在协程内部再调 `asyncio.run()` → `RuntimeError: cannot be called from a running event loop`

**生活化类比**：`asyncio.run` = 拧钥匙**点火启动**；`await` = 已经在开，**踩油门/挂挡**。你都已经在车里开着了（`async def` 里），不能再拧钥匙点火，只能继续踩油门。

**前端类比**：`asyncio.run()` 对应 JS 里「最外层那一句 `add(2, 3)`」（启动），而不是函数里的 `await`。Python 只是把「启动」这个动作显式暴露成了一个函数，所以它只能出现在最外层同步代码。

### 并发 vs 顺序

```python
# 顺序：总耗时 = 1+1+1 = 3 秒
for d in [1, 1, 1]:
    await asyncio.sleep(d)

# 并发：总耗时 ≈ 1 秒（IO 等待时间重叠）
await asyncio.gather(
    asyncio.sleep(1),
    asyncio.sleep(1),
    asyncio.sleep(1),
)
```

核心价值：**IO 等待的时间可以重叠**，和 `Promise.all` 同理。

### 常用 API 速查

```python
import asyncio

asyncio.run(coro)              # 启动事件循环（最外层）
await coro                     # 协程内等待
asyncio.sleep(seconds)         # 异步等待，单位是秒
asyncio.gather(c1, c2, ...)    # 并发执行，返回结果列表
asyncio.gather(*list_of_coros) # list 要先 * 展开
asyncio.create_task(coro)      # 包装成 Task，后台先跑，稍后 await
asyncio.iscoroutine(obj)       # 判断是否是协程对象
```

---

## 二、练习纠错全记录（本次会话交流）

### 第一轮：初次提交 → 6 个练习都有错

用户第一版代码的问题清单：

| 练习 | 用户的写法 | 问题 |
|------|-----------|------|
| 1 greet | `return f"Hello {name}!"` | 少逗号，期望 `"Hello, World!"` |
| 2 add_with_await | `x1 = asyncio.run(double(a))` + 多余 `await asyncio.sleep(1)` | 核心概念错误（asyncio.run 误用） |
| 3 fetch_delay | `await asyncio.sellp(seconds)` | 拼写笔误（sellp → sleep） |
| 4 run_concurrently | `await asyncio.gather(arr)` | list 没 `*` 展开 |
| 5 make_tasks | `await asyncio.gather([task1, task2])` | 同上 |
| 6 run_sequentially | `await asyncio.run(fetch_delay(x))` + 无 `return` | asyncio.run 误用 + 缺返回值 |

### 报错 1：`asyncio.run()` 不能嵌套调用

```
RuntimeError: asyncio.run() cannot be called from a running event loop
```

**诊断**：练习 2 里，`add_with_await` 已经被外层的 `asyncio.run(add_with_await(...))` 启动了，它本身就在事件循环里跑。此时内部再调 `asyncio.run(double(a))`，等于「在运行中的循环里再新建一个循环」，Python 直接拒绝。

**用户的追问**：「练习 2，为啥是你说的这样？」

**深入讲解**：`asyncio.run()` 不是一个「执行 async 函数」的通用工具，它是**冷启动入口**。Python 里执行协程只有两种方式，互斥：

- 同步代码里 → `asyncio.run(coro)`
- 异步代码里 → `await coro`

**修正**：练习 2 和 6 里的 `asyncio.run(...)` 全部改成 `await ...`，删掉多余的 `sleep(1)`。

### 第二轮：练习 1/2/3 通过，剩 3 个问题

练习 1、2、3 全部通过 ✅（说明 `asyncio.run` vs `await` 的概念已理解）。

但练习 4、5、6 没改，卡在：

```
TypeError: cannot use 'list' as a dict key (unhashable type: 'list')
```

**诊断**：`asyncio.gather(arr)` 把整个 `arr`（list）当成**一个参数**传进去。`gather` 的签名是 `gather(*args)`，期望一个个独立的协程。它内部拿这个参数当字典 key，list 不能当 key，于是炸了。

**讲解 `*` 展开**：

```python
asyncio.gather(arr)    # gather 收到 1 个参数（一个 list）→ ❌
asyncio.gather(*arr)   # 拆成 3 个独立的协程 → ✅
# 等价于：
asyncio.gather(fetch_delay(1), fetch_delay(1), fetch_delay(1))
```

这个 `*` 就是 0.2 数据结构学过的**解包**（`print(*[1,2,3])` == `print(1,2,3)`）。

**修正**：
- 练习 4：`gather(arr)` → `gather(*arr)`
- 练习 5：`gather([task1, task2])` → `gather(task1, task2)`
- 练习 6：for 循环已对，补上 `time.perf_counter()` 计时和 `return`

### 第三轮：全部通过 🎉

```
✅ 练习1 greet
✅ 练习2 add_with_await
✅ 练习3 fetch_delay
✅ 练习4 并发耗时 1.02s ≈ 1s
✅ 练习5 make_tasks
✅ 练习6 顺序耗时 3.04s ≈ 3s
🎉 全部通过！0.5 异步基础 = ✅
```

练习 4/6 的计时验证（并发 ≈1s、顺序 ≈3s）证明了「IO 等待时间重叠」真正被理解。

---

## 三、踩坑速查

| 错误写法 | 报错 | 正确写法 |
|---------|------|---------|
| 协程内 `asyncio.run(x)` | `RuntimeError: ... running event loop` | `await x` |
| `asyncio.gather(arr)` | `TypeError: unhashable type: 'list'` | `asyncio.gather(*arr)` |
| `asyncio.sellp()` | `AttributeError` | `asyncio.sleep()` |
| `asyncio.sleep(1000)`（想等 1 秒） | 等 1000 秒 | `asyncio.sleep(1)`（单位是秒） |
| 创建协程但没 await | `RuntimeWarning: coroutine was never awaited` | 记得 `await` 或交给 `run`/`gather` |
