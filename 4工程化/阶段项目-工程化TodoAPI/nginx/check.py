"""
Task 4 · Nginx 自动验证（不要修改这个文件）

用法（在项目目录下）：
    ../../.venv/bin/python nginx/check.py

它做的事：
1. 建好测试库表（eng_todo_test_db，Redis 用 db 14）
2. 起两个 uvicorn 实例：8001（api-1）/ 8002（api-2）
3. 用 nginx/nginx.conf 起 nginx（8088）
4. 逐项验证：静态文件 / SPA 回退 / API 转发（剥前缀）/ 请求头透传 / 轮询
5. 不管成败，结束时关掉所有进程

在 nginx.conf 填完之前，它会停在「语法检查失败」—— 这是正常的。
"""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx

BASE = Path(__file__).resolve().parent          # .../nginx
PROJECT = BASE.parent                            # 项目目录
NGINX = shutil.which("nginx") or "/opt/homebrew/bin/nginx"

BASE_URL = "http://127.0.0.1:8088"
BACKEND_PORTS = (8001, 8002)
TEST_DATABASE_URL = "postgresql+psycopg:///eng_todo_test_db"
TEST_REDIS_URL = "redis://127.0.0.1:6379/14"

uvicorn_procs = []
errors = []


def expect(ok, label, detail=""):
    if ok:
        print(f"  ✅ {label}")
    else:
        print(f"  ❌ {label}")
        if detail:
            print(f"     {detail}")
        errors.append(label)


def port_free(port):
    with socket.socket() as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def nginx_cmd(*args):
    return [NGINX, "-p", str(BASE), "-c", str(BASE / "nginx.conf"), *args]


def start_uvicorn(port, instance):
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL
    env["REDIS_URL"] = TEST_REDIS_URL
    env["INSTANCE"] = instance
    env["PYTHONPATH"] = str(PROJECT)
    p = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "wrapped_app:app",
            "--host", "127.0.0.1", "--port", str(port),
            "--log-level", "warning",
        ],
        cwd=str(BASE),
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    uvicorn_procs.append(p)
    return p


def wait_ready(client, url, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            client.get(url, timeout=0.5)
            return True
        except httpx.HTTPError:
            time.sleep(0.2)
    return False


def prepare_tables():
    """测试库的表可能被 pytest 结束时 drop 掉，这里保证它们存在。"""
    env = os.environ.copy()
    env["DATABASE_URL"] = TEST_DATABASE_URL
    env["PYTHONPATH"] = str(PROJECT)
    code = "import models; from database import Base, engine; Base.metadata.create_all(engine)"
    r = subprocess.run([sys.executable, "-c", code], cwd=str(PROJECT), env=env,
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("❌ 准备测试库失败：")
        print(r.stderr.strip())
        return False
    return True


def flush_test_redis():
    env = os.environ.copy()
    env["REDIS_URL"] = TEST_REDIS_URL
    env["PYTHONPATH"] = str(PROJECT)
    code = "import cache; cache.redis_client.flushdb()"
    subprocess.run([sys.executable, "-c", code], cwd=str(PROJECT), env=env,
                   capture_output=True)


def stop_all():
    subprocess.run(nginx_cmd("-s", "stop"), capture_output=True)
    for p in uvicorn_procs:
        if p.poll() is None:
            p.terminate()
    for p in uvicorn_procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def main():
    if not Path(NGINX).exists():
        print("❌ 找不到 nginx，先 brew install nginx")
        return 1

    busy = [str(p) for p in (*BACKEND_PORTS, 8088) if not port_free(p)]
    if busy:
        print(f"❌ 端口被占用：{', '.join(busy)}（可能是上次没退干净的进程）")
        return 1

    (BASE / "runtime").mkdir(exist_ok=True)

    # 先做语法检查：配置写错直接看报错，不起任何进程
    result = subprocess.run(nginx_cmd("-t"), capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ nginx.conf 语法检查失败：")
        print((result.stderr or result.stdout).strip())
        return 1

    if not prepare_tables():
        return 1
    flush_test_redis()

    print("启动 uvicorn 8001(api-1) / 8002(api-2) + nginx 8088 ...")
    start_uvicorn(8001, "api-1")
    start_uvicorn(8002, "api-2")

    client = httpx.Client(base_url=BASE_URL, timeout=5, trust_env=False)
    wait_ready(client, f"http://127.0.0.1:{BACKEND_PORTS[0]}/docs", timeout=15)

    subprocess.run(nginx_cmd("-s", "stop"), capture_output=True)  # 清残留
    start = subprocess.run(nginx_cmd(), capture_output=True, text=True)
    if start.returncode != 0:
        print("❌ nginx 启动失败：")
        print((start.stderr or start.stdout).strip())
        return 1
    if not wait_ready(client, "/", timeout=5):
        print("❌ nginx 起来了但 8088 没响应")
        return 1

    try:
        # ==========================================================
        # 1. 静态文件 + SPA 回退
        # ==========================================================
        print("\n===== 1. 静态文件 + SPA 回退 =====")
        r = client.get("/")
        expect(
            r.status_code == 200 and "Todo SPA" in r.text,
            "GET / 返回 static/index.html",
            f"实际 {r.status_code}，body 前 80 字：{r.text[:80]!r}",
        )
        r = client.get("/hello.txt")
        expect(
            r.status_code == 200 and "真实的静态文件" in r.text,
            "GET /hello.txt 返回真实文件",
            f"实际 {r.status_code}，body 前 80 字：{r.text[:80]!r}",
        )
        r = client.get("/assets/app.js")
        expect(r.status_code == 200, "GET /assets/app.js 能取到", f"实际 {r.status_code}")
        r = client.get("/todos/123")
        expect(
            r.status_code == 200 and "Todo SPA" in r.text,
            "GET /todos/123 回退到 index.html（前端路由刷新不 404）",
            f"实际 {r.status_code}，body 前 80 字：{r.text[:80]!r}",
        )

        # ==========================================================
        # 2. API 转发（剥 /api 前缀）
        # ==========================================================
        print("\n===== 2. API 转发 =====")
        username = f"nginx_{uuid4().hex[:8]}"
        password = "pass12345"

        r = client.post("/api/auth/register", json={"username": username, "password": password})
        expect(
            r.status_code == 201,
            "POST /api/auth/register → 201（后端收到的是 /auth/register）",
            f"实际 {r.status_code} {r.text[:120]}；404 说明 proxy_pass 没剥前缀或没转发",
        )

        token = None
        r = client.post("/api/auth/login", data={"username": username, "password": password})
        if r.status_code == 200:
            token = r.json().get("access_token")
        expect(r.status_code == 200 and isinstance(token, str),
               "POST /api/auth/login → 200 拿到 access_token",
               f"实际 {r.status_code} {r.text[:120]}")

        headers = {"Authorization": f"Bearer {token}"} if token else {}
        r = client.post("/api/todos", json={"title": "走 nginx 创建的"}, headers=headers)
        todo_id = r.json().get("id") if r.status_code == 201 else None
        expect(r.status_code == 201, "POST /api/todos → 201", f"实际 {r.status_code} {r.text[:120]}")

        r = client.get("/api/todos", headers=headers)
        expect(
            r.status_code == 200 and any(t.get("id") == todo_id for t in r.json()),
            "GET /api/todos 能看到刚创建的 todo",
            f"实际 {r.status_code} {r.text[:120]}",
        )

        r = client.get("/api/nope")
        expect(
            r.status_code == 404 and r.headers.get("content-type", "").startswith("application/json"),
            "GET /api/nope → 404 JSON（没被 SPA 回退成 index.html）",
            f"实际 {r.status_code} content-type={r.headers.get('content-type')!r}",
        )

        # ==========================================================
        # 3. 请求头透传
        # ==========================================================
        print("\n===== 3. 请求头透传 =====")
        r = client.get("/api/debug/headers")
        data = r.json() if r.status_code == 200 else {}
        expect(r.status_code == 200, "GET /api/debug/headers → 200", f"实际 {r.status_code}")
        expect(
            bool(data.get("x_real_ip")) and data["x_real_ip"] == "127.0.0.1",
            "X-Real-IP 透传到后端",
            f"后端 x_real_ip={data.get('x_real_ip')!r}（None = 没配 proxy_set_header X-Real-IP）",
        )
        expect(
            "127.0.0.1" in (data.get("x_forwarded_for") or ""),
            "X-Forwarded-For 透传到后端",
            f"后端 x_forwarded_for={data.get('x_forwarded_for')!r}（None = 没配，或变量用错）",
        )
        expect(
            bool(data.get("host")) and "8001" not in data["host"] and "8002" not in data["host"],
            "Host 头是客户端的（不是后端的 127.0.0.1:8001）",
            f"后端 host={data.get('host')!r}（应配 proxy_set_header Host $host）",
        )

        # ==========================================================
        # 4. upstream 轮询
        # ==========================================================
        print("\n===== 4. upstream 轮询 =====")
        seen = []
        for _ in range(6):
            r = client.get("/api/debug/headers")
            seen.append(r.headers.get("x-instance", "?"))
        expect(
            "api-1" in seen and "api-2" in seen,
            "6 次请求两个实例都应答了（轮询）",
            f"实际序列：{seen}；全是同一个说明 proxy_pass 没指向 upstream",
        )

    finally:
        client.close()
        stop_all()
        flush_test_redis()

    print()
    if errors:
        print(f"还有 {len(errors)} 项没通过，改完 nginx.conf 再跑一次。")
        return 1
    print("🎉 全部通过！Task 4 的 Nginx 部分 = ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
