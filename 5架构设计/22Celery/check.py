"""
22 Celery + Redis — 真实 worker 端到端验证

做法：
  1. 清空 Redis db0（broker）和 db1（backend）
  2. 起一个真实的 celery worker 子进程（--pool=solo，macOS 上更稳）
  3. 主进程扮演 FastAPI：只投递任务、查状态，不执行任务
  4. 断言任务确实由「另一个进程」执行、状态会流转

运行：../../.venv/bin/python check.py
"""

import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

import redis
from celery.result import AsyncResult
from kombu.exceptions import EncodeError

from celery_app import app
import practice

PY = sys.executable
LOG = HERE / "worker.log"


def flush_redis():
    for db in (0, 1):
        redis.Redis(db=db).flushdb()


def start_worker():
    log = open(LOG, "w")
    proc = subprocess.Popen(
        [PY, "-m", "celery", "-A", "practice", "worker",
         "--pool=solo", "-c", "1", "-l", "info"],
        cwd=HERE,
        stdout=log,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    deadline = time.time() + 25
    while time.time() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"worker 启动失败，看 {LOG}")
        text = LOG.read_text(errors="ignore")
        if "ready." in text:
            return proc
        time.sleep(0.2)
    raise RuntimeError(f"worker 25 秒没就绪，看 {LOG}")


results = []


def check(name, cond, expected, actual):
    if cond:
        print(f"✅ {name}")
        results.append(True)
    else:
        print(f"❌ {name}：期望 {expected}，实际 {actual}")
        results.append(False)


def main():
    flush_redis()
    worker = start_worker()
    print("worker 已就绪，开始投递任务…\n")
    try:
        # 1. 投递立刻返回，不阻塞
        t0 = time.time()
        slow = practice.slow_add.delay(2, 3, 1.5)
        elapsed = time.time() - t0
        check("投递慢任务耗时可忽略（<0.5s）", elapsed < 0.5, "<0.5s", f"{elapsed:.3f}s")

        # 2. 刚投递时任务还没跑完
        check("刚投递时状态不是 SUCCESS", slow.state != "SUCCESS", "PENDING/STARTED", slow.state)

        # 3. 结果由 worker 算出来
        check("1.5 秒后拿到正确结果", slow.get(timeout=15) == 5, 5, slow.result)
        check("完成后状态是 SUCCESS", slow.state == "SUCCESS", "SUCCESS", slow.state)

        # 4. 进程隔离：任务在别的进程里执行
        pid = practice.who_am_i.delay().get(timeout=10)
        check("任务运行在另一个进程", pid != os.getpid(), f"≠ {os.getpid()}", pid)

        # 5. 失败任务：状态和异常
        f = practice.fail_task.delay("炸了")
        exc = f.get(timeout=10, propagate=False)
        check("失败任务结果是 ValueError", isinstance(exc, ValueError), "ValueError", type(exc).__name__)
        check("失败任务状态是 FAILURE", f.state == "FAILURE", "FAILURE", f.state)
        check("失败任务带 traceback", bool(f.traceback), "非空", f.traceback)

        # 6. 重试：两次失败后成功
        fl = practice.flaky_task.delay()
        check("重试后最终成功", fl.get(timeout=20) == 2, 2, fl.result)

        # 7. 参数必须能 JSON 序列化
        try:
            practice.fail_task.delay(object())
            raised = "没有报错"
        except EncodeError as e:
            raised = f"EncodeError: {str(e)[:40]}…"
        check("传不可序列化对象会被拒绝", raised.startswith("EncodeError"), "EncodeError", raised)

        # 8. 不存在的 task_id 也报 PENDING
        check(
            "未知 task_id 的状态是 PENDING",
            AsyncResult("00000000-0000-0000-0000-000000000000", app=app).state == "PENDING",
            "PENDING",
            AsyncResult("00000000-0000-0000-0000-000000000000", app=app).state,
        )

        # 9. beat 配置就绪（不启动 beat，只验证配置）
        entry = practice.BEAT_SCHEDULE.get("add-every-5-minutes", {})
        check(
            "beat 调度配置指向 task",
            entry.get("task") == practice.add.name,
            practice.add.name,
            entry.get("task"),
        )

        print()
        if all(results):
            print(f"🎉 {len(results)} 项全部通过：真实 worker 跑通了")
            LOG.unlink(missing_ok=True)
            return 0
        print(f"有 {results.count(False)} 项没通过")
        return 1
    finally:
        worker.terminate()
        try:
            worker.wait(timeout=10)
        except subprocess.TimeoutExpired:
            worker.kill()
        flush_redis()


if __name__ == "__main__":
    sys.exit(main())
