"""
第五阶段 · 22 Celery + Redis

Celery app 实例：生产者（web 进程）和 worker 都从同一个「邮局地址」收发任务。
这个文件不用改。

broker  = 收件箱，任务消息进这里（Redis db0）
backend = 回执箱，任务结果和状态存这里（Redis db1）
"""

from celery import Celery

app = Celery(
    "practice",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
)
