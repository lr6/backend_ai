"""
第一阶段 · 3 FastAPI 进阶 — 检验练习

每个 TODO 需要你来实现。
写完后运行: .venv/bin/python practice.py
全部通过 = FastAPI 进阶 ✅

提示（前端对照）：
  - Depends          ~ 自定义 Hook，复用逻辑
  - 中间件 (middleware) ~ axios 拦截器，请求/响应统一处理
  - 生命周期 (lifespan) ~ useEffect 挂载/卸载
"""

from fastapi import FastAPI, Depends, Header
from fastapi.testclient import TestClient
from contextlib import asynccontextmanager
import time


# ===== 练习 3：生命周期（Lifespan）=====
# 注意：lifespan 要最先定义，因为创建 app 时就要传给它
lifecycle_events = []


@asynccontextmanager
async def lifespan(app):
    """
    生命周期：yield 之前 = 应用启动时执行；yield 之后 = 应用关闭时执行。
    """
    lifecycle_events.append("startup")
    # TODO: 写 yield，表示「应用正常运行期间」（就一行）
    yield
    lifecycle_events.append("shutdown")


app = FastAPI(lifespan=lifespan)


# ===== 练习 1：Depends（依赖注入）=====
def get_current_user(x_username: str = Header(default="anonymous")):
    """
    依赖函数：从请求头 X-Username 读取当前用户名，没有则默认 "anonymous"。
    这个函数会被 Depends 自动调用，返回值注入到路由参数里。
    """
    return x_username


@app.get("/me")
def me(user: str = Depends(get_current_user)):
    """
    返回当前用户：{"username": user}

    user 由上面的依赖函数自动注入，不用手动调用 get_current_user()。
    你只需要把 user 放进返回的 dict 里。
    """
    # TODO
    return { 'username': user }


# ===== 练习 2：中间件（Middleware）=====
@app.middleware("http")
async def add_process_time(request, call_next):
    """
    中间件：请求前记下开始时间，请求后计算耗时，写进响应头 X-Process-Time。

    结构是固定的：
      - await call_next(request) 会让请求继续往下走（进入路由），拿到 response
      - 在它之后写 response.headers[...] = ...，再 return response
    """
    start = time.time()
    response = await call_next(request)
    process_time = time.time() - start
    # TODO: 把 process_time 写入响应头 "X-Process-Time"（注意要转成字符串 str()）
    response.headers['X-Process-Time'] = str(process_time)
    return response


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    client = TestClient(app)
    errors = []

    def check(name, actual, expected):
        if actual != expected:
            errors.append(f"{name}: 期望 {expected}，实际 {actual}")
        else:
            print(f"✅ {name}")

    # 练习 1：Depends（依赖注入）
    r = client.get("/me")
    check("练习1 无头默认 anonymous", r.json().get("username"), "anonymous")
    r = client.get("/me", headers={"X-Username": "zhibo"})
    check("练习1 带头发 zhibo", r.json().get("username"), "zhibo")

    # 练习 2：中间件（给响应加 X-Process-Time 头）
    r = client.get("/me")
    check("练习2 有 X-Process-Time 头", "X-Process-Time" in r.headers, True)

    # 练习 3：生命周期（用 with 触发完整的启动/关闭）
    with TestClient(app) as client_lifecycle:
        check("练习3 启动事件", "startup" in lifecycle_events, True)
        client_lifecycle.get("/me")
    check("练习3 关闭事件", "shutdown" in lifecycle_events, True)

    if errors:
        print(f"\n有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("\n🎉 全部通过！FastAPI 进阶 = ✅")
