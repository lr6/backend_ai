#!/usr/bin/env python3
"""
第五阶段 · 21 Docker — 检验脚本

用法：
  python check.py            # 练习 1：Dockerfile（build + run + 访问 /greeting）
  python check.py --part2    # 练习 2：docker-compose（app + postgres + redis）
  python check.py --all      # 两个都跑

前置：Docker Desktop 已启动（docker ps 不报错）。
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP_DIR = ROOT / "app"

IMAGE = "docker-practice-app"
CONTAINER = "practice-app"
PART1_PORT = 8099
PART2_PORT = 8090


# ============================================
# 工具函数
# ============================================
def sh(cmd, cwd=None, timeout=600):
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )


def get_json(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read())


def post_json(url, timeout=15):
    req = urllib.request.Request(url, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def wait_json(url, seconds=90, **kwargs):
    """反复请求 url，直到拿到 JSON 或超时。返回 None 表示超时。"""
    deadline = time.time() + seconds
    last_err = None
    while time.time() < deadline:
        try:
            return get_json(url)
        except Exception as exc:  # 连接被拒 / 502 / 还没起来
            last_err = exc
            time.sleep(1)
    print(f"   （最后一次错误：{last_err}）")
    return None


def wait_health(url, seconds=90):
    """等到 /health 里 db 和 redis 都是 up。"""
    deadline = time.time() + seconds
    last = None
    while time.time() < deadline:
        try:
            last = get_json(url)
            if last.get("db") == "up" and last.get("redis") == "up":
                return last
        except Exception:
            pass
        time.sleep(2)
    print(f"   （最后一次 /health：{last}）")
    return None


def docker_ready():
    r = sh(["docker", "info"])
    if r.returncode != 0:
        print("❌ Docker 守护进程没起来，先启动 Docker Desktop")
        sys.exit(1)


class Report:
    def __init__(self):
        self.errors = []

    def check(self, cond, label, detail=""):
        if cond:
            print(f"  ✅ {label}")
        else:
            print(f"  ❌ {label}")
            if detail:
                print(f"     期望/实际：{detail}")
            self.errors.append(label)

    def fail(self, label):
        print(f"  ❌ {label}")
        self.errors.append(label)

    def done(self, title):
        print()
        if self.errors:
            print(f"有 {len(self.errors)} 个测试没通过：")
            for e in self.errors:
                print("  " + e)
            return 1
        print(f"🎉 全部通过！{title} = ✅")
        return 0


# ============================================
# 练习 1：Dockerfile
# ============================================
def part1():
    print("== 练习 1：Dockerfile ==")
    rep = Report()
    dockerfile = APP_DIR / "Dockerfile"

    if not dockerfile.exists():
        rep.fail("找不到 app/Dockerfile")
        return rep.done("练习 1")

    text = dockerfile.read_text(encoding="utf-8")
    for instr in ["FROM", "WORKDIR", "COPY", "RUN", "CMD"]:
        if instr not in text.upper():
            rep.fail(f"Dockerfile 缺 {instr} 指令")

    print("  构建镜像中（第一次可能要一两分钟）…")
    build = sh(["docker", "build", "-t", IMAGE, str(APP_DIR)])
    if build.returncode != 0:
        rep.fail("docker build 失败")
        print("\n--- 构建输出末尾 ---")
        print(build.stdout[-2000:] + build.stderr[-2000:])
        return rep.done("练习 1")
    rep.check(True, "docker build 成功")

    sh(["docker", "rm", "-f", CONTAINER])
    run = sh(
        ["docker", "run", "-d", "--name", CONTAINER, "-p", f"{PART1_PORT}:8000", IMAGE]
    )
    if run.returncode != 0:
        rep.fail("docker run 失败")
        print(run.stderr[-800:])
        return rep.done("练习 1")
    rep.check(True, f"容器启动成功（宿主机 {PART1_PORT} → 容器 8000）")

    # CMD 没写对的话容器会立刻退出
    time.sleep(2)
    ps = sh(["docker", "ps", "--filter", f"name={CONTAINER}", "--format", "{{.Status}}"])
    if "Up" not in ps.stdout:
        logs = sh(["docker", "logs", CONTAINER]).stdout + sh(["docker", "logs", CONTAINER]).stderr
        rep.fail("容器没在运行（CMD 写错了？）")
        print("\n--- 容器日志 ---")
        print(logs[-1500:])
        return rep.done("练习 1")
    rep.check(True, "容器是 Up 状态")

    greeting = wait_json(f"http://127.0.0.1:{PART1_PORT}/greeting", seconds=60)
    rep.check(
        greeting == {"greeting": "hello from docker"},
        "GET /greeting 返回 hello from docker",
        f"实际：{greeting}",
    )

    health = wait_json(f"http://127.0.0.1:{PART1_PORT}/health", seconds=20)
    rep.check(
        isinstance(health, dict) and health.get("app") == "ok",
        "GET /health 返回 app=ok（db/redis 是 down 属于正常）",
        f"实际：{health}",
    )

    if not rep.errors:
        print(f"\n  💡 浏览器打开 http://127.0.0.1:{PART1_PORT}/docs 能看 Swagger")
        print(f"  💡 容器还留着，看完可以删：docker rm -f {CONTAINER}")

    return rep.done("练习 1")


# ============================================
# 练习 2：docker-compose
# ============================================
def compose(*args):
    return sh(["docker", "compose", *args], cwd=ROOT, timeout=900)


def part2():
    print("== 练习 2：docker-compose ==")
    rep = Report()

    # 造一个假的本地产物，验证 .dockerignore 有没有挡住它
    junk_dir = APP_DIR / "__pycache__"
    junk_dir.mkdir(exist_ok=True)
    (junk_dir / "_junk.pyc").write_text("this should never reach the image")
    try:
        return _part2_body(rep)
    finally:
        shutil.rmtree(junk_dir, ignore_errors=True)


def _part2_body(rep):
    compose_file = ROOT / "docker-compose.yml"
    if not compose_file.exists():
        rep.fail("找不到 docker-compose.yml")
        return rep.done("练习 2")

    print("  启动全部服务中（第一次 build + 拉 postgres/redis 可能要几分钟）…")
    up = compose("up", "-d", "--build")
    if up.returncode != 0:
        rep.fail("docker compose up 失败")
        print("\n--- 输出末尾 ---")
        print(up.stdout[-2000:] + up.stderr[-2000:])
        return rep.done("练习 2")
    rep.check(True, "docker compose up -d --build 成功")

    ls = compose("exec", "-T", "app", "ls", "-a", "/app")
    rep.check(
        ls.returncode == 0 and "__pycache__" not in ls.stdout,
        ".dockerignore 生效：本机的 __pycache__ 没被拷进镜像",
        f"镜像里 /app 下有：{ls.stdout.split() if ls.stdout else ls.stderr[-200:]}",
    )

    base = f"http://127.0.0.1:{PART2_PORT}"
    health = wait_health(f"{base}/health", seconds=120)
    rep.check(
        health is not None,
        "GET /health 返回 db=up 且 redis=up（服务名能互相解析）",
        f"实际：{health}",
    )

    greeting = wait_json(f"{base}/greeting", seconds=30)
    rep.check(
        greeting == {"greeting": "hello from compose"},
        "环境变量 GREETING 从 compose 传进了容器",
        f"实际：{greeting}",
    )

    try:
        v1 = post_json(f"{base}/visits")
        v2 = post_json(f"{base}/visits")
        rep.check(
            v2.get("visits") == v1.get("visits", 0) + 1,
            "POST /visits 能往 postgres 写数据",
            f"第一次 {v1}，第二次 {v2}",
        )
        before = v2.get("visits")
    except Exception as exc:
        rep.fail(f"POST /visits 失败：{exc}")
        before = None

    print("  重启全部容器，验证数据卷是否持久化…")
    compose("down")
    up2 = compose("up", "-d")
    if up2.returncode != 0:
        rep.fail("docker compose 第二次 up 失败")
        print(up2.stderr[-1000:])
        return rep.done("练习 2")

    health2 = wait_health(f"{base}/health", seconds=120)
    rep.check(health2 is not None, "重启后服务恢复", f"实际：{health2}")

    if before is not None:
        try:
            v3 = post_json(f"{base}/visits")
            rep.check(
                v3.get("visits") == before + 1,
                "docker compose down/up 之后数据还在（volume 生效）",
                f"重启前 {before}，重启后 {v3}",
            )
        except Exception as exc:
            rep.fail(f"重启后 POST /visits 失败：{exc}")

    if not rep.errors:
        print("\n  💡 清理：docker compose down -v")

    return rep.done("练习 2")


# ============================================
# 入口
# ============================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--part2", action="store_true", help="跑练习 2")
    parser.add_argument("--all", action="store_true", help="两个练习都跑")
    args = parser.parse_args()

    docker_ready()

    code = 0
    if args.all or not args.part2:
        code |= part1()
    if args.all or args.part2:
        print()
        code |= part2()
    sys.exit(code)
