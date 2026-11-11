"""
第三阶段 · 14 CORS — 检验练习

每个函数的 TODO 需要你来实现。
写完后运行: .venv/bin/python practice.py
全部通过 = 14 CORS 过关 ✅

依赖: fastapi、httpx（均已安装）

说明：
- 练习用 TestClient 模拟浏览器发出的跨域请求（带 Origin 头）。
- TestClient 不会真的执行同源策略，它只是让你检查「服务器回了什么头」，
  浏览器是否放行由这些头决定。
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

ORIGIN = "http://localhost:5173"


# ===== 练习 1：判断简单请求 =====
def is_simple_request(method: str, headers: list[str], content_type: str | None) -> bool:
    """
    判断一个跨域请求是否属于「简单请求」（不触发预检）。

    规则（必须全部满足）:
        1. method 只能是 GET / HEAD / POST（不区分大小写）
        2. headers 里只能出现安全头: accept, accept-language, content-language, content-type
           （比较时不区分大小写）
        3. content_type 只能是 application/x-www-form-urlencoded、multipart/form-data、text/plain
           （content_type 为 None 表示没带这个头，算满足）

    例如:
        is_simple_request("GET", [], None) -> True
        is_simple_request("POST", [], "application/json") -> False
        is_simple_request("GET", ["Authorization"], None) -> False
    """
    if method.lower() not in ("get", "head", "post"):
        return False

    safe_header = {"accept", "accept-language", "content-language", "content-type"}
    for h in headers:
        if h.lower() not in safe_header:
            return False

    if content_type is not None and content_type not in (
        "application/x-www-form-urlencoded",
        "multipart/form-data","text/plain"
    ):
        return False

    return True


# ===== 练习 2：基础 CORS 应用 =====
def create_app(allowed_origins: list[str]) -> FastAPI:
    """
    创建一个带 CORS 配置的 FastAPI 应用。

    要求:
        1. app = FastAPI()
        2. app.add_middleware(
               CORSMiddleware,
               allow_origins=allowed_origins,
               allow_methods=["*"],
               allow_headers=["*"],
               max_age=600,
           )
        3. 返回 app

    ⚠️ allow_methods / allow_headers 必须显式写，默认值只有 GET / 空，
       不写的话预检会直接 400（坑 1）。

    测试会给返回的 app 追加一个 /ping 路由再用 TestClient 请求。
    """
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        max_age=600
    )
    return app


# ===== 练习 3：模拟 CORS 对账（纯逻辑） =====
def cors_headers_for(origin: str, allowed_origins: list[str]) -> dict[str, str]:
    """
    模拟浏览器与服务器「对账」：给定请求的 Origin 和允许列表，
    返回应该附在响应上的 CORS 头；不允许则返回空 dict。

    要求:
        - 精确字符串比较：协议、域名、端口、末尾斜杠，任何一个不同都不算命中
        - 命中 -> {"Access-Control-Allow-Origin": origin}
        - 未命中 -> {}

    例如:
        cors_headers_for("http://localhost:5173", ["http://localhost:5173"])
        -> {"Access-Control-Allow-Origin": "http://localhost:5173"}

        cors_headers_for("http://localhost:5173/", ["http://localhost:5173"])
        -> {}
    """
    if origin in allowed_origins:
        return {"Access-Control-Allow-Origin": origin}
    return {}


# ===== 练习 4：允许携带 cookie 的 CORS =====
def create_credential_app(allowed_origins: list[str]) -> FastAPI:
    """
    创建一个允许前端携带 cookie（axios withCredentials / fetch credentials）
    的 FastAPI 应用。

    要求:
        1. CORSMiddleware
        2. allow_credentials=True
        3. allow_origins 使用传入的明确列表 —— 绝不能改成 ["*"]（坑 2）
        4. allow_methods=["*"], allow_headers=["*"]

    测试会给返回的 app 追加一个 /me 路由。
    """
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
        max_age=600
    )
    return app


# ===== 练习 5：开发环境的动态端口 =====
def create_dev_app() -> FastAPI:
    """
    Vite 端口可能在 5173 / 5174 之间跳，用 allow_origin_regex 放行
    所有 http://localhost:<任意端口>。

    要求:
        1. CORSMiddleware
        2. allow_origin_regex 放行 http://localhost:<端口>（5173、3000、8000 都算）
        3. https://localhost:5173、http://127.0.0.1:5173、http://evil.com 都不放行
        4. allow_methods=["*"], allow_headers=["*"]

    提示: Starlette 用正则整串匹配，写 r"http://localhost:\\d+"

    测试会给返回的 app 追加一个 /x 路由。
    """
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://localhost:\d+",
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
        max_age=600
    )
    return app


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    errors = []

    def cors_headers(r):
        return {
            k: v for k, v in r.headers.items()
            if k.lower().startswith("access-control")
        }

    def check(label, cond, msg):
        if not cond:
            errors.append(f"{label}: {msg}")

    # ---------- 练习 1 ----------
    simple_cases = [
        (("GET", [], None), True),
        (("get", [], None), True),
        (("HEAD", [], None), True),
        (("POST", [], "text/plain"), True),
        (("POST", [], "application/x-www-form-urlencoded"), True),
        (("POST", [], "multipart/form-data"), True),
        (("GET", ["Accept", "Accept-Language"], None), True),
        (("GET", [], "application/json"), False),
        (("GET", ["Authorization"], None), False),
        (("GET", ["authorization"], None), False),
        (("GET", ["Accept", "X-Custom"], None), False),
        (("POST", [], "application/json"), False),
        (("DELETE", [], None), False),
        (("PUT", [], "text/plain"), False),
    ]
    for args, expected in simple_cases:
        try:
            actual = is_simple_request(*args)
            if actual != expected:
                errors.append(
                    f"练习1{args}: 期望 {expected}，实际 {actual!r}"
                )
        except Exception as e:
            errors.append(f"练习1{args}: 运行出错 {type(e).__name__}: {e}")

    # ---------- 练习 2 ----------
    try:
        app2 = create_app([ORIGIN])
        app2.add_api_route("/ping", lambda: {"ok": True})
        c2 = TestClient(app2)

        r = c2.get("/ping", headers={"Origin": ORIGIN})
        check("练习2(允许的源)", r.status_code == 200 and r.headers.get("access-control-allow-origin") == ORIGIN,
              f"期望 200 + ACAO={ORIGIN}，实际 {r.status_code} {cors_headers(r)}")

        r = c2.get("/ping", headers={"Origin": "http://evil.com"})
        check("练习2(未知的源)", "access-control-allow-origin" not in r.headers,
              f"未知源不应拿到 ACAO，实际 {cors_headers(r)}")

        r = c2.options("/ping", headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        })
        allow_methods = (r.headers.get("access-control-allow-methods") or "").upper()
        allow_headers = (r.headers.get("access-control-allow-headers") or "").lower()
        check("练习2(预检)", r.status_code == 200 and r.headers.get("access-control-allow-origin") == ORIGIN,
              f"期望 200 + ACAO，实际 {r.status_code} {cors_headers(r)}")
        check("练习2(预检 POST)", "POST" in allow_methods,
              f"预检应允许 POST，实际 allow-methods={allow_methods!r}")
        check("练习2(预检 authorization)", "authorization" in allow_headers,
              f"预检应允许 authorization，实际 allow-headers={allow_headers!r}")
        check("练习2(max_age)", r.headers.get("access-control-max-age") == "600",
              f"期望 max-age=600，实际 {r.headers.get('access-control-max-age')!r}")

        r = c2.options("/ping", headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST",
        })
        check("练习2(未知源的预检)", r.status_code == 400 and "access-control-allow-origin" not in r.headers,
              f"未知源的预检应 400 且无 ACAO，实际 {r.status_code} {cors_headers(r)}")
    except Exception as e:
        errors.append(f"练习2: 运行出错 {type(e).__name__}: {e}")

    # ---------- 练习 3 ----------
    header_cases = [
        ((ORIGIN, [ORIGIN]), {"Access-Control-Allow-Origin": ORIGIN}),
        (("http://localhost:5173/", [ORIGIN]), {}),
        (("http://localhost:5174", [ORIGIN]), {}),
        (("https://localhost:5173", [ORIGIN]), {}),
        (("http://127.0.0.1:5173", [ORIGIN]), {}),
        (("http://localhost:5173", []), {}),
        (("http://a.com", ["http://a.com", "http://b.com"]), {"Access-Control-Allow-Origin": "http://a.com"}),
    ]
    for args, expected in header_cases:
        try:
            actual = cors_headers_for(*args)
            if actual != expected:
                errors.append(f"练习3{args}: 期望 {expected}，实际 {actual!r}")
        except Exception as e:
            errors.append(f"练习3{args}: 运行出错 {type(e).__name__}: {e}")

    # ---------- 练习 4 ----------
    try:
        origins4 = [ORIGIN, "http://localhost:3000"]
        app4 = create_credential_app(origins4)
        app4.add_api_route("/me", lambda: {"user": "alice"})
        c4 = TestClient(app4)

        r = c4.get("/me", headers={"Origin": ORIGIN})
        acao = r.headers.get("access-control-allow-origin")
        acac = r.headers.get("access-control-allow-credentials")
        check("练习4(带 cookie)", r.status_code == 200 and acao == ORIGIN and acac == "true",
              f"期望 ACAO={ORIGIN} + ACAC=true，实际 {r.status_code} {cors_headers(r)}")
        check("练习4(不能用通配)", acao != "*",
              f"带 credentials 时 ACAO 不能是 *，实际 {acao!r}")

        r = c4.get("/me", headers={"Origin": "http://localhost:3000"})
        check("练习4(第二个源)", r.headers.get("access-control-allow-origin") == "http://localhost:3000",
              f"期望放行 3000，实际 {cors_headers(r)}")

        r = c4.get("/me", headers={"Origin": "http://evil.com"})
        check("练习4(未知的源)", "access-control-allow-origin" not in r.headers,
              f"未知源不应拿到 ACAO（说明没有写成 *），实际 {cors_headers(r)}")

        r = c4.options("/me", headers={
            "Origin": ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization",
        })
        check("练习4(预检)", r.status_code == 200
              and r.headers.get("access-control-allow-credentials") == "true"
              and r.headers.get("access-control-allow-origin") == ORIGIN,
              f"预检应 200 + ACAO + ACAC，实际 {r.status_code} {cors_headers(r)}")
    except Exception as e:
        errors.append(f"练习4: 运行出错 {type(e).__name__}: {e}")

    # ---------- 练习 5 ----------
    try:
        app5 = create_dev_app()
        app5.add_api_route("/x", lambda: {})
        c5 = TestClient(app5)

        for ok_origin in ["http://localhost:5173", "http://localhost:3000",
                          "http://localhost:8000"]:
            r = c5.get("/x", headers={"Origin": ok_origin})
            if r.headers.get("access-control-allow-origin") != ok_origin:
                errors.append(
                    f"练习5({ok_origin}): 应放行，实际 {cors_headers(r)}"
                )

        for bad_origin in ["https://localhost:5173", "http://127.0.0.1:5173",
                           "http://evil.com", "http://localhost:5173.evil.com"]:
            r = c5.get("/x", headers={"Origin": bad_origin})
            if "access-control-allow-origin" in r.headers:
                errors.append(
                    f"练习5({bad_origin}): 不应放行，实际 {cors_headers(r)}"
                )
    except Exception as e:
        errors.append(f"练习5: 运行出错 {type(e).__name__}: {e}")

    # ---------- 汇总 ----------
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！14 CORS = ✅")
