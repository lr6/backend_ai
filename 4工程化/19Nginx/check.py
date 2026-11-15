"""
第 19 项 Nginx · 自动测试（不要修改这个文件）

用法：
    python check.py

它会：
1. 起两个 uvicorn 回声服务（8000 / 8001）
2. 用本目录的 nginx.conf 起 nginx（8080）
3. 用 httpx 打 8080，逐项验证 5 个练习
4. 不管成败，结束后把 nginx 和 uvicorn 全部关掉

只跑这一个文件，不要手动再起 uvicorn / nginx 占端口。
"""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

BASE = Path(__file__).resolve().parent
NGINX = shutil.which("nginx") or "/opt/homebrew/bin/nginx"
BASE_URL = "http://127.0.0.1:8080"

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


def start_uvicorn(port):
    env = os.environ.copy()
    env["PORT"] = str(port)
    p = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "app:app",
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


def nginx_cmd(*args):
    return [NGINX, "-p", str(BASE), "-c", str(BASE / "nginx.conf"), *args]


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

    busy = [str(p) for p in (8000, 8001, 8080) if not port_free(p)]
    if busy:
        print(f"❌ 端口被占用：{', '.join(busy)}")
        print("   先关掉占用的进程（可能是上次没退干净的 nginx / uvicorn）。")
        return 1

    (BASE / "runtime").mkdir(exist_ok=True)

    # 语法检查先做，配置写错的话直接给报错，不去起进程
    result = subprocess.run(nginx_cmd("-t"), capture_output=True, text=True)
    if result.returncode != 0:
        print("❌ nginx.conf 语法检查失败：")
        print((result.stderr or result.stdout).strip())
        return 1

    print("启动两个 uvicorn（8000 / 8001）+ nginx（8080）...")
    start_uvicorn(8000)
    start_uvicorn(8001)

    client = httpx.Client(base_url=BASE_URL, timeout=5, trust_env=False)
    if not wait_ready(client, "/"):
        pass  # 后端是否就绪稍后由用例体现，nginx 起不来更关键

    subprocess.run(nginx_cmd("-s", "stop"), capture_output=True)  # 清掉上次残留
    start = subprocess.run(nginx_cmd(), capture_output=True, text=True)
    if start.returncode != 0:
        print("❌ nginx 启动失败：")
        print((start.stderr or start.stdout).strip())
        return 1
    if not wait_ready(client, "/", timeout=5):
        print("❌ nginx 起来了但 8080 没响应")
        return 1

    try:
        # ==========================================================
        # 练习 1：静态文件 + SPA 回退
        # ==========================================================
        print("\n===== 练习 1：静态文件 + SPA 回退 =====")
        r = client.get("/")
        expect(
            r.status_code == 200 and "Nginx 静态页" in r.text,
            "GET / 返回 static/index.html",
            f"实际状态码 {r.status_code}，body 前 80 字：{r.text[:80]!r}",
        )
        r = client.get("/hello.txt")
        expect(
            r.status_code == 200 and "真实的静态文件" in r.text,
            "GET /hello.txt 返回真实文件内容",
            f"实际状态码 {r.status_code}，body 前 80 字：{r.text[:80]!r}",
        )
        r = client.get("/about")
        expect(
            r.status_code == 200 and "Nginx 静态页" in r.text,
            "GET /about 回退到 index.html（try_files）",
            f"实际状态码 {r.status_code}，body 前 80 字：{r.text[:80]!r}",
        )

        # ==========================================================
        # 练习 2：反向代理 + 前缀剥离
        # ==========================================================
        print("\n===== 练习 2：反向代理 =====")
        r = client.get("/api/hello")
        data = None
        if r.status_code == 200:
            try:
                data = r.json()
            except ValueError:
                data = None
        path = data.get("path") if data else None
        hint = ""
        if path == "/api/hello":
            hint = " 后端收到的路径没剥前缀：proxy_pass 末尾少了 /（对比表的第 2 行）"
        elif r.status_code in (404, 502):
            hint = " 404/502 说明 /api/ 还没转发到后端：检查 location /api/ 里的 proxy_pass"
        expect(
            path == "/hello",
            "GET /api/hello → 后端收到 /hello（前缀被替换）",
            f"实际状态码 {r.status_code}，后端 path = {path!r}。{hint}",
        )

        # ==========================================================
        # 练习 3：真实 IP / Host 透传
        # ==========================================================
        print("\n===== 练习 3：请求头透传 =====")
        if data:
            x_real_ip = data.get("x_real_ip")
            xff = data.get("x_forwarded_for") or ""
            host = data.get("host_header") or ""
            expect(
                x_real_ip == "127.0.0.1",
                "X-Real-IP 透传到后端",
                f"后端 x_real_ip = {x_real_ip!r}（None = 没配 proxy_set_header X-Real-IP）",
            )
            expect(
                "127.0.0.1" in xff,
                "X-Forwarded-For 透传到后端",
                f"后端 x_forwarded_for = {xff!r}（None = 没配，或用错了变量）",
            )
            expect(
                host and ":8000" not in host,
                "Host 头被改写（不再是 nginx 默认的 127.0.0.1:8000）",
                f"后端 host_header = {host!r}",
            )
        else:
            print("  ⏭️  练习 2 没通过，跳过（这里要复用 /api/hello 的响应）")

        # ==========================================================
        # 练习 4：负载均衡
        # ==========================================================
        print("\n===== 练习 4：负载均衡 =====")
        ports = []
        for i in range(6):
            r = client.get(f"/api/whoami?i={i}")
            if r.status_code == 200:
                try:
                    ports.append(str(r.json().get("port")))
                except ValueError:
                    ports.append("?")
            else:
                ports.append(f"HTTP {r.status_code}")
        both = "8000" in ports and "8001" in ports
        hint = ""
        if ports.count("8000") == len(ports):
            hint = " 全落在 8000：proxy_pass 还在直连 127.0.0.1:8000，没指向 upstream todo_cluster"
        elif any(str(x).startswith("HTTP") for x in ports):
            hint = " 有请求失败：检查 upstream 名字是否和 proxy_pass 里的一致"
        expect(
            both,
            "连续 6 次请求，8000 和 8001 都有应答（轮询）",
            f"实际端口序列：{ports}。{hint}",
        )

        # ==========================================================
        # 练习 5：location 匹配优先级
        # ==========================================================
        print("\n===== 练习 5：location 匹配优先级 =====")
        cases = [
            ("/health", "exact", ""),
            (
                "/img/logo.png",
                "caret_tilde",
                " 返回 regex 说明正则先命中了：^~ 的作用是「前缀命中后不再检查正则」",
            ),
            ("/files/a.png", "regex", ""),
        ]
        for path, want, hint in cases:
            r = client.get(path)
            got = r.text.strip()
            expect(
                r.status_code == 200 and got == want,
                f"GET {path} → {want}",
                f"实际：{r.status_code} {got[:60]!r}。{hint}",
            )

    finally:
        client.close()
        stop_all()

    print()
    if errors:
        print(f"还有 {len(errors)} 项没通过，继续填 TODO 再跑一次。")
        return 1
    print("🎉 全部通过！学习项 19 的配置部分 = ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
