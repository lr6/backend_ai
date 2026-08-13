"""
第零阶段 · 0.5 异步基础 — 检验练习

每个函数的 TODO 需要你来实现。
写完后运行: python practice.py
全部通过 = 0.5 异步基础 ✅

提示（前端对照）：
  - async def  ~  JS 的 async function
  - await      ~  JS 的 await
  - asyncio.gather(...)  ~  Promise.all([...])
  - asyncio.sleep(秒)    ~  setTimeout(毫秒)，但单位是秒
"""

import asyncio
import time


# ===== 练习 1：定义协程函数 =====
async def greet(name: str) -> str:
    """
    返回问候语 "Hello, {name}!"
    例如: greet("World") -> "Hello, World!"
    """
    # TODO: 返回字符串
    return f"Hello, {name}!"


# ===== 练习 2：await 另一个协程 =====
async def double(x: int) -> int:
    """
    返回 x * 2
    例如: double(3) -> 6
    """
    # TODO: 返回 x * 2
    return x * 2


async def add_with_await(a: int, b: int) -> int:
    """
    用 await 调用 double，返回 double(a) + double(b)
    例如: add_with_await(2, 3) -> 10
    """
    # TODO: 用 await 调用 double 两次并相加
    x1 = await double(a)
    x2 = await double(b)
    return x1 + x2

# ===== 练习 3：用 asyncio.sleep 模拟 IO =====
async def fetch_delay(seconds: float) -> float:
    """
    用 asyncio.sleep(seconds) 模拟一个耗时的 IO 操作（比如网络请求），
    等完后返回传入的 seconds。
    例如: fetch_delay(1.5) -> 1.5
    """
    # TODO: await asyncio.sleep(seconds)，然后返回 seconds
    await asyncio.sleep(seconds)
    return seconds


# ===== 练习 4：并发执行（gather）=====
async def run_concurrently(delays: list[float]) -> float:
    """
    用 asyncio.gather 并发执行 fetch_delay 对 delays 中的每个元素。
    返回总耗时（秒），用 time.perf_counter() 记录前后时间差。

    如果 delays = [1, 1, 1]，并发执行总耗时应该约 1 秒（而不是 3 秒）。

    提示：先把每个 delay 变成协程对象，再用 gather 一起执行。
    """
    # TODO
    t1 = time.perf_counter()
    arr = []
    for x in delays:
        arr.append(fetch_delay(x))
    await asyncio.gather(*arr)
    t2 = time.perf_counter()
    return t2 - t1


# ===== 练习 5：create_task 提前创建任务 =====
async def make_tasks() -> list[str]:
    """
    用 asyncio.create_task 创建两个任务：
      - task1 = greet("Alice")
      - task2 = greet("Bob")
    然后 await 它们，返回 [task1 的结果, task2 的结果]
    例如: make_tasks() -> ["Hello, Alice!", "Hello, Bob!"]
    """
    # TODO
    task1 = asyncio.create_task(greet("Alice"))
    task2 = asyncio.create_task(greet("Bob"))
    arr = await asyncio.gather(task1, task2)
    return arr


# ===== 练习 6：顺序执行 =====
async def run_sequentially(delays: list[float]) -> float:
    """
    用 for 循环依次 await fetch_delay（不要用 gather），
    返回总耗时（秒）。

    如果 delays = [1, 1, 1]，顺序执行总耗时应该约 3 秒。
    """
    # TODO
    t1 = time.perf_counter()
    for x in delays:
        await fetch_delay(x)
    t2 = time.perf_counter()
    return t2 - t1


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []

    def check(name, actual, expected):
        if actual != expected:
            errors.append(f"{name}: 期望 {expected}，实际 {actual}")
        else:
            print(f"✅ {name}")

    # 练习 1：greet 必须是协程函数
    coro = greet("World")
    if asyncio.iscoroutine(coro):
        check("练习1 greet", asyncio.run(coro), "Hello, World!")
    else:
        errors.append("练习1: greet 不是协程（要用 async def 定义）")

    # 练习 2：await 另一个协程
    check("练习2 add_with_await", asyncio.run(add_with_await(2, 3)), 10)

    # 练习 3：模拟 IO
    check("练习3 fetch_delay", asyncio.run(fetch_delay(0.1)), 0.1)

    # 练习 4：并发，约 1 秒
    t = asyncio.run(run_concurrently([1, 1, 1]))
    if abs(t - 1.0) < 0.5:
        print(f"✅ 练习4 并发耗时 {t:.2f}s ≈ 1s")
    else:
        errors.append(f"练习4: 并发耗时 {t:.2f}s，应该约 1s（是不是没用 gather？）")

    # 练习 5：create_task
    check("练习5 make_tasks", asyncio.run(make_tasks()), ["Hello, Alice!", "Hello, Bob!"])

    # 练习 6：顺序，约 3 秒
    t = asyncio.run(run_sequentially([1, 1, 1]))
    if abs(t - 3.0) < 0.5:
        print(f"✅ 练习6 顺序耗时 {t:.2f}s ≈ 3s")
    else:
        errors.append(f"练习6: 顺序耗时 {t:.2f}s，应该约 3s")

    if errors:
        print(f"\n有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("\n🎉 全部通过！0.5 异步基础 = ✅")
