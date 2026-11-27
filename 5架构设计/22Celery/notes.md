# 22 Celery + Redis — 异步任务队列、定时任务

> 环境：项目 `.venv` 安装 `celery 5.7.0`（`pip install "celery[redis]"`），Redis 本机 `6379`。
> broker 用 Redis db0，result backend 用 db1。macOS 上 worker 用 `--pool=solo` 更稳。
>
> 文件：
> - `celery_app.py` — Celery 实例（broker / backend / 序列化配置）
> - `practice.py` — 6 个练习 + eager 模式自动测试
> - `check.py` — 真实 worker 端到端 12 项断言（自己起 worker 子进程）
> - `notes.md` — 本文件

---

## 一、知识点讲解

### 1. 为什么需要 Celery：`async def` ≠ 后台任务

`async def` 解决的是「一个进程在等 I/O 时别闲着」，让事件循环在多个请求之间切换。但活仍然在 web 进程里干，客户端仍然要等这次请求返回；CPU 重的活（生成报表、处理图片）还会把事件循环整个卡住。

Celery 解决的是另一件事：**活根本不在 web 进程里干**。

- 接口把任务丢进队列，立刻返回「已提交」；
- 客户端不用等；
- worker 可以单独扩容、单独重启；
- web 进程崩了不影响已经在队列里的任务。

前端类比：`async/await` 像页面里 `await fetch()`，页面不卡但你还是等结果；Celery 像调用接口拿到一个 `jobId`，结果过会儿再查。

### 2. 四大件（寄快递类比）

| 角色 | 类比 | 本项目的实现 |
|------|------|--------------|
| broker | 邮局 / 快递柜 | Redis db0 |
| producer | 寄件人 | FastAPI 代码里的 `.delay()` |
| worker | 快递员 | `celery -A practice worker` |
| result backend | 签收回执 | Redis db1 |

`.delay()` 把「任务名 + 参数」序列化成 JSON 投进 broker；worker 取出来执行；结果写进 backend，凭 `task_id` 查。

### 3. 进程隔离的三个后果

worker 和 web 是两个独立进程，各自内存互不可见：

1. **拿不到请求对象 / 全局 Session**。`Depends(get_db)` 在 worker 里不会执行。
2. **参数必须可 JSON 序列化**。只能传字符串、数字、dict、list。传 ORM 对象、Session 会在投递时报 `EncodeError`。正确做法：传 `todo_id`，worker 里自己 `with SessionLocal() as db:` 查库。
3. **任务里要自己管理资源**，用完关连接。

抽查题「接口异步发邮件，任务函数收什么参数」→ 用户答 `todo_id` ✅。

### 4. 投递：`.delay()` 到底在干什么

`@app.task` 装饰后，`add` 是 Task 对象，不是普通函数：

- `add(2, 3)` → 当前进程同步执行，返回 5，Celery 没参与；
- `add.delay(2, 3)` → **只投递，不执行**，返回 `AsyncResult` 句柄，`.id` 是运单号；
- `add.apply_async(args=[2, 3], countdown=10)` → 功能更全的版本（倒计时、指定队列、过期时间），`.delay` 是它的简写。

worker 没启动时 `.delay()` **不会报错**，消息照样进 Redis，任务一直 PENDING——生产最常见坑之一。

### 5. 查结果：`AsyncResult(task_id, app=app)`

结果对象跨请求不能复用，能跨请求传的只有 `task_id`；GET 时用 id 重建 `AsyncResult` 去 backend 查。

为什么要 `app=app`：`AsyncResult` 需要知道「去哪查」（`result_backend`）和「怎么解析」（序列化配置）。不带时用 Celery 的 `current_app`，单 app 一般能用，但多 app / 跨进程时容易指错。显式传更稳，类似显式传 Session。

状态：

- `PENDING` — 还没执行 **或** 任务不存在 **或** worker 没起（三者无法区分）；
- `STARTED` — 需要 `task_track_started=True`；
- `SUCCESS` / `FAILURE`。

失败任务：异常对象存在 backend 里，`result.get(propagate=False)` 返回异常对象本身，`propagate=True` 重新抛出；`.traceback` 是 worker 里的调用栈。

### 6. 确认语义（ack）

默认 `acks_late=False`：worker **开始执行前**就确认收货。所以验证：

- 消息还在队列里时 worker 崩了 → 重启后继续执行，不丢；
- **正在执行**的那条 worker 崩了 → 丢了。
- 要「至少执行一次」：`acks_late=True`，代价是可能重复执行，任务必须幂等。

### 7. 重试：不是循环，是重新投递

```python
@app.task(bind=True, max_retries=5, default_retry_delay=0.1)
def flaky_task(self) -> int:
    if self.request.retries < 2:
        raise self.retry(exc=ValueError("还没成功"))
    return self.request.retries
```

- `bind=True` → 第一个参数 `self` 是任务实例，能拿 `self.request`；
- `self.request.retries`：第一次执行是 0，每重试一次 +1；
- `self.retry(...)` **抛 `Retry` 异常**，Celery 接住后按 `countdown` 把同一任务重新塞回队列，当前执行结束；
- 所以写 `raise self.retry(...)`，不是 `return`；
- **每次重试都是全新执行**，局部变量不会保留——次数只能从 `self.request.retries` 或外部存储拿；
- 超过 `max_retries` → `FAILURE`，异常是 `MaxRetriesExceededError`（包着原异常）；
- 生产常用指数退避 `retry_backoff=True`；装饰器写法 `autoretry_for=(ValueError,)` 可以自动重试指定异常。

前端类比：像 axios 拦截器失败后重新发一次请求，而不是原地 `while` 重试。

### 8. 定时任务：beat 是第三个进程

```python
BEAT_SCHEDULE = {
    "add-every-5-minutes": {
        "task": add.name,
        "schedule": crontab(minute="*/5"),
        "args": (1, 2),
    },
}
app.conf.beat_schedule = BEAT_SCHEDULE
```

- beat **只负责按时间投递**，不执行任务；执行仍是 worker。生产要同时跑 `beat` + `worker`；
- beat 一般只跑一个实例，跑多个会重复投递；
- `crontab(minute="*/5")` = 0、5、10… 每 5 分钟；
- `"task"` 用 `add.name`，别手写 `"practice.add"`：任务全名是「模块名.函数名」，入口不同（`__main__` / `practice`）会不一致。

### 9. 测试：eager 模式 vs 真实 worker

- `task_always_eager=True`：`.delay()` 同步执行，不碰 broker/worker → `practice.py` 的测试不用起 worker；
- 但 eager 把 broker 和 worker 全绕过了，**绿了只证明任务逻辑对**；
- 真实行为必须看 `check.py`：起 worker 子进程、走 Redis、断言投递不阻塞 / 任务在另一个 PID 执行 / 状态流转 / 重试 / 序列化拦截；
- eager 结果默认不写 backend，需要 `task_store_eager_result=True`（且任务对象上也要打开），否则 `AsyncResult` 查到 PENDING。

---

## 二、练习 ↔ 知识点映射

| 练习 | 内容 | 对应知识点 |
|------|------|-----------|
| 1 | `add` 任务 | `@app.task`、任务体就是普通函数体、`.delay` 属于调用方 |
| 2 | `slow_add` / `who_am_i` | 进程隔离、PID 不同、慢任务不阻塞投递 |
| 3 | `fail_task` | FAILURE 状态、异常存 backend、`get(propagate=)` |
| 4 | `flaky_task` | `bind=True`、`self.request.retries`、`raise self.retry` |
| 5 | FastAPI 两个接口 | `.delay().id` 立刻返回、`AsyncResult(task_id, app=app)` 查回执 |
| 6 | `BEAT_SCHEDULE` | beat 调度、crontab、任务名用 `add.name` |

---

## 三、练习纠错全记录

### 探底问答

- Q1「`async def` 能并发处理请求，为什么还要 Celery？」→ 用户答**不知道**。讲解：async 是「一个进程内等 I/O 时切走」，活还在 web 进程里干、客户端还得等；Celery 是「活交给另一拨进程」。
- Q2「1000 封邮件丢给 Celery 后 worker 崩了会怎样？」→ 用户答「一封都没发出去？还是发了几封剩下的没发？」。方向对：队列里的任务在 Redis 里活着，正在执行的那条默认已 ack，会丢。
- 检查题「web 进程重启，队列里的任务丢不丢？」→ 答「不会，web 进程和这个事情毫无联系」✅。

### 练习 1：在任务体里又 `.delay` 自己

- 现象：用户写 `def add(x, y): add.delay(2, 3).get()`
- 原因：混淆了「投递方」和「执行方」。函数体是 worker 要跑的代码，再调 `.delay` 等于执行时又投递自己，无限套娃，而且没有 return。
- 解决：函数体只写 `return x + y`；`.delay(2, 3).get()` 属于测试/调用方。
- 知识点：`@app.task` 装饰后，函数体 = 业务逻辑。

### 练习 2：一次写对

- `slow_add`：`time.sleep(seconds)` 后 `return x + y`；
- `who_am_i`：`return os.getpid()`。

### 练习 3：一次写对

- `raise ValueError(message)`。

### 练习 4：不会 → 讲解 → 用户要求直接给答案

- 现象：用户说「还是不太确定，先讲讲原理」，讲解后又要求「直接把答案写出来」。
- 讲解要点：`self.retry()` 抛 `Retry`；每次重试是新执行；局部变量不保留；第三次执行 `retries == 2`。
- Claude 写入答案并逐行解释。
- 知识点：重试 = 重新投递，不是循环。

### 练习 5：拼写 + 返回对象

用户先自己写了两段，发现的问题：

1. `{"tsak_id": ...}` — 键名拼错成 `tsak_id`。**不报错**，只是返回里没有 `task_id`，后续 GET 查不到。测试里表现为 `task_id` 为 None。
2. `return celery.result.AsyncResult(task_id, app=app)` — 两个问题：
   - `celery` 这个名字没 import（顶部是 `from celery.result import AsyncResult`）→ `NameError`；
   - `AsyncResult` 是对象，不能直接当 JSON 返回（500）。要取 `.state` / `.result` 拼 dict。
3. 用户随后要求直接给答案，Claude 写入：

```python
@api.post("/tasks/add")
def create_add_task(payload: AddRequest):
    return {"task_id": add.delay(payload.x, payload.y).id}

@api.get("/tasks/{task_id}")
def get_task(task_id: str):
    result = AsyncResult(task_id, app=app)
    return {"state": result.state, "result": result.result}
```

- 知识点：跨请求只能传 task_id；结果在 backend，凭 id 查。GET 里没有复用 POST 的对象，也不需要。

### 练习 6：不会 → 直接给配置 + 讲解

- 用户说「我也不会写」。
- Claude 写入 `BEAT_SCHEDULE`，讲清四个字段 + beat 是独立进程 + beat 单实例。

### 用户主动提问（= 不懂，必须记）

1. **`.delay()` 是在干啥？** → 只投递不执行；`add(2,3)` 才是执行；`.delay` = `apply_async` 简写；返回句柄不是结果。
2. **为什么 `AsyncResult(task_id, app=app)` 要 `app=app`？** → 查结果需要知道 backend 地址和序列化配置，都在 app 里；不带会用 `current_app`，多 app / 跨进程易错。
3. 追问「worker 没启动，`.delay` 会报错吗？」→ 不会，消息照进 Redis，任务一直 PENDING。

### Claude 自己的 bug（记录）

- `practice.py` 测试脚本在练习 5 未实现时崩溃：接口返回 `null`，`resp.json()` 是 `None`，`body.get(...)` 抛 `AttributeError`，导致前面的 ❌ 都没打印出来。
- 修复：`body = (resp.json() or {}) if ...`；`except ValueError` 放宽为 `except Exception`。
- `check.py` 序列化检查最初写 `add.delay(object())`，因参数个数不对先报 `TypeError` 而不是 `EncodeError`；改用 `fail_task.delay(object())`。
- eager 模式结果默认不写 backend 的坑，用 `store_eager_result = True` 在测试里显式打开。

---

## 四、踩坑速查表

| 错误写法 / 现象 | 原因 | 正确写法 |
|----------------|------|---------|
| 任务体里写 `add.delay(...)` | 执行时又投递自己，无限套娃 | 函数体只写业务逻辑 `return x + y` |
| `{"tsak_id": ...}` | 拼写错，静默返回错误键名 | `"task_id"` |
| `return AsyncResult(...)` | 对象不可 JSON 序列化，500 | `return {"state": r.state, "result": r.result}` |
| `celery.result.AsyncResult(...)` | 没 import `celery` 名字，NameError | `AsyncResult(...)`（顶部已导入） |
| 手写 `"practice.add"` 作任务名 | 入口不同模块名不同（`__main__`） | `add.name` |
| 传 ORM 对象 / Session 给任务 | 不是 JSON，投递报 `EncodeError` | 传 id，worker 内自建 Session |
| 传 `object()` 且参数个数不对 | 先抛 `TypeError`，看不到序列化错误 | 参数个数要对，才轮到 `EncodeError` |
| 用局部变量数重试次数 | 每次重试是全新执行，变量重置 | `self.request.retries` |
| `return self.retry(...)` | `retry` 是抛异常不是返回值 | `raise self.retry(exc=...)` |
| 状态一直 PENDING | worker 没起 / 任务不存在 / 还在排队（三者同状态） | 查 worker 进程、`celery inspect` |
| eager 测试绿了以为异步没问题 | eager 绕过了 broker/worker | 跑 `check.py` 真实 worker 验证 |
| 生产里 worker 崩了任务丢 | 默认执行前 ack（`acks_late=False`） | `acks_late=True` + 任务幂等 |

---

## 五、运行方式

```bash
cd 5架构设计/22Celery

# 1. 逻辑测试（eager，不用 worker）
../../.venv/bin/python practice.py

# 2. 真实 worker 端到端（脚本自己起 worker）
../../.venv/bin/python check.py

# 3. 手动起 worker（可选）
../../.venv/bin/celery -A practice worker --pool=solo -l info
# 4. 手动起 beat（可选）
../../.venv/bin/celery -A practice beat -l info
```
