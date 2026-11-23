"""
Task 4 验证用的包装 app —— 不属于业务代码，只是给 check.py 提供观测点。

在 main.py 的 app 外面加两样东西：
1. 响应头 X-Instance：值是 INSTANCE 环境变量（api-1 / api-2），用来证明 upstream 轮询
2. GET /debug/headers：回显 nginx 透传过来的请求头，用来验证 proxy_set_header 三件套

启动时由 check.py 负责，不要手动起。
"""

import os

from fastapi import Request

from main import app

INSTANCE = os.environ.get("INSTANCE", "unknown")


@app.get("/debug/headers", tags=["debug"])
def debug_headers(request: Request):
    return {
        "instance": INSTANCE,
        "host": request.headers.get("host"),
        "x_real_ip": request.headers.get("x-real-ip"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
        "client": request.client.host if request.client else None,
    }


@app.middleware("http")
async def add_instance_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Instance"] = INSTANCE
    return response
