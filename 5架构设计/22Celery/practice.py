"""
第五阶段 · 22 Celery + Redis — 检验练习

每个 TODO 需要你来实现。
运行 python practice.py 时任务在「当前进程同步执行」（eager 模式），不用起 worker；
真实 worker 的验证在 check.py。

启动真实 worker（另开一个终端，在 22Celery 目录下）：
  ../../.venv/bin/celery -A practice worker --pool=solo -l info
"""

import os
import time

from celery.result import AsyncResult
from celery.schedules import crontab
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from celery_app import app


# ===== 练习 1：定义一个任务 =====
@app.task
def add(x: int, y: int) -> int:
    """把两个数相加并返回。
    add.delay(2, 3).get() → 5
    """
    return x + y


# ===== 练习 2：慢任务 + 进程身份 =====
@app.task
def slow_add(x: int, y: int, seconds: float = 1.0) -> int:
    """先睡 seconds 秒，再返回 x + y。
    用来观察「接口不阻塞」和 PENDING / STARTED 状态。
    """
    time.sleep(seconds)
    return x + y


@app.task
def who_am_i() -> int:
    """返回执行本任务的进程 PID。真实 worker 里跑时，它和 web 进程的 PID 不同。"""
    return os.getpid()


# ===== 练习 3：会失败的任务 =====
@app.task
def fail_task(message: str) -> None:
    """永远抛 ValueError(message)。用来观察 FAILURE 状态和异常。
    """
    raise ValueError(message)


# ===== 练习 4：会重试的任务 =====
@app.task(bind=True, max_retries=5, default_retry_delay=0.1)
def flaky_task(self) -> int:
    """前两次执行都失败并重试，第三次成功。
    成功时返回「已经重试了几次」→ 2

    提示：self.request.retries 是当前是第几次重试（从 0 开始）；
         self.retry(exc=ValueError("还没成功")) 会抛 Retry 让 Celery 重新排队。
    """
    if self.request.retries < 2:
        raise self.retry(exc=ValueError("还没成功"))
    return self.request.retries


# ===== 练习 5：FastAPI 集成 =====
api = FastAPI(title="Celery 练习")


class AddRequest(BaseModel):
    x: int
    y: int


@api.post("/tasks/add")
def create_add_task(payload: AddRequest):
    """提交任务，立刻返回 {"task_id": "..."}（不要等任务跑完）。"""
    return {"task_id": add.delay(payload.x, payload.y).id}


@api.get("/tasks/{task_id}")
def get_task(task_id: str):
    """按 task_id 查状态，返回 {"state": "...", "result": ...}

    提示：celery.result.AsyncResult(task_id, app=app)
    """
    result = AsyncResult(task_id, app=app)
    return {"state": result.state, "result": result.result}


# ===== 练习 6：定时任务配置 =====
# 让 Celery beat 每 5 分钟执行一次 add(1, 2)。
# 提示：crontab(minute="*/5")；task 名字用 add.name 取，别手写，避免模块名对不上。
BEAT_SCHEDULE = {
    "add-every-5-minutes": {
        "task": add.name,
        "schedule": crontab(minute="*/5"),
        "args": (1, 2),
    },
}

app.conf.beat_schedule = BEAT_SCHEDULE


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    # eager 模式：任务在当前进程里同步执行，测试不需要 worker。
    # 真实 worker 的行为由 check.py 验证。
    app.conf.update(
        task_always_eager=True,
        task_store_eager_result=True,
        task_eager_propagates=False,
    )
    # 测试专用：eager 执行的结果默认不写 backend，这里打开，GET 接口才能查到。
    for _task in (add, slow_add, who_am_i, fail_task, flaky_task):
        _task.store_eager_result = True

    errors = []

    def check(name, cond, expected, actual):
        if cond:
            print(f"✅ {name}")
        else:
            errors.append(f"❌ {name}：期望 {expected}，实际 {actual}")

    # 练习 1
    r = add.delay(2, 3)
    check("练习1 add.delay(2, 3)", r.get() == 5, 5, r.get())
    check("练习1 任务名以 .add 结尾", add.name.endswith(".add"), "*.add", add.name)

    # 练习 2
    check("练习2 slow_add", slow_add.delay(2, 3, 0.0).get() == 5, 5, slow_add.delay(2, 3, 0.0).get())
    check("练习2 who_am_i 返回 PID", who_am_i.delay().get() == os.getpid(), os.getpid(), who_am_i.delay().get())

    # 练习 3
    f = fail_task.delay("炸了")
    check("练习3 状态是 FAILURE", f.state == "FAILURE", "FAILURE", f.state)
    check("练习3 存的是 ValueError", isinstance(f.result, ValueError), "ValueError", type(f.result).__name__)
    try:
        fail_task.delay("炸了").get(propagate=True)
        raised = False
        got = "没有抛异常"
    except Exception as e:
        raised = True
        got = str(e)
    check("练习3 get(propagate=True) 抛 ValueError", raised and got == "炸了", "ValueError('炸了')", got)

    # 练习 4
    fl = flaky_task.delay()
    check("练习4 重试后成功", fl.state == "SUCCESS", "SUCCESS", fl.state)
    check("练习4 返回值是重试次数", fl.result == 2, 2, fl.result)

    # 练习 5
    client = TestClient(api)
    resp = client.post("/tasks/add", json={"x": 2, "y": 3})
    body = (resp.json() or {}) if resp.status_code == 200 else {}
    task_id = body.get("task_id")
    check("练习5 POST 返回 200", resp.status_code == 200, 200, resp.status_code)
    check("练习5 POST 返回 task_id", isinstance(task_id, str) and len(task_id) > 0, "非空字符串", repr(task_id))

    if task_id:
        resp2 = client.get(f"/tasks/{task_id}")
        body2 = (resp2.json() or {}) if resp2.status_code == 200 else {}
        check("练习5 GET 状态 SUCCESS", body2.get("state") == "SUCCESS", "SUCCESS", body2.get("state"))
        check("练习5 GET 结果 5", body2.get("result") == 5, 5, body2.get("result"))
    else:
        errors.append("❌ 练习5：没有 task_id，GET 无法测试")

    # 练习 6
    entry = BEAT_SCHEDULE.get("add-every-5-minutes", {})
    check("练习6 有条目", bool(entry), "存在", "缺失")
    check("练习6 task 指向 add", entry.get("task") == add.name, add.name, entry.get("task"))
    check("练习6 schedule 是 crontab", isinstance(entry.get("schedule"), crontab), "crontab", type(entry.get("schedule")).__name__)
    check("练习6 args 是 (1, 2)", entry.get("args") == (1, 2), "(1, 2)", entry.get("args"))

    # ============================================
    if errors:
        print(f"\n有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("\n🎉 全部通过！22 Celery + Redis = ✅")
