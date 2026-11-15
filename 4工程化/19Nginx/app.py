"""
第 19 项 Nginx · 练习用回声服务（不要修改这个文件）

它做三件事：
1. 告诉你「我是哪个端口的进程」（8000 还是 8001）
2. 回显「我最终收到的路径」（用来验证 proxy_pass 有没有剥前缀）
3. 回显「我看到的客户端信息」（用来验证代理有没有透传 X-Real-IP / Host）

启动方式由 check.py 负责，不要手动起。
"""

import os

from fastapi import FastAPI, Request

app = FastAPI()
PORT = os.environ.get("PORT", "8000")


@app.get("/{path:path}")
async def echo(path: str, request: Request):
    return {
        "port": PORT,
        "path": "/" + path,
        "client": request.client.host if request.client else None,
        "host_header": request.headers.get("host"),
        "x_real_ip": request.headers.get("x-real-ip"),
        "x_forwarded_for": request.headers.get("x-forwarded-for"),
    }
