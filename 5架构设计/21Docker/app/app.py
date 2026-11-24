"""
第五阶段 · 21 Docker — 练习用的最小 FastAPI 应用

这个文件已经写好，不用改。你负责给它写 Dockerfile 和 docker-compose.yml。

接口：
  GET  /greeting  → {"greeting": <环境变量 GREETING 的值>}
  GET  /health    → {"app": "ok", "db": "up|down", "redis": "up|down"}
                     （练习 1 没有数据库，db/redis 显示 down 是正常的）
  POST /visits    → {"visits": N}   往数据库插一条并返回总数
"""

import os

import psycopg
import redis
from fastapi import FastAPI

app = FastAPI()

DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")
GREETING = os.getenv("GREETING", "hello from docker")


@app.get("/greeting")
def greeting():
    return {"greeting": GREETING}


@app.get("/health")
def health():
    result = {"app": "ok", "db": "down", "redis": "down"}

    if DATABASE_URL:
        try:
            with psycopg.connect(DATABASE_URL, connect_timeout=2) as conn:
                conn.execute("SELECT 1")
            result["db"] = "up"
        except Exception as exc:
            result["db_error"] = str(exc)[:120]

    if REDIS_URL:
        try:
            if redis.from_url(REDIS_URL, socket_connect_timeout=2).ping():
                result["redis"] = "up"
        except Exception as exc:
            result["redis_error"] = str(exc)[:120]

    return result


@app.post("/visits")
def add_visit():
    with psycopg.connect(DATABASE_URL, connect_timeout=3) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS visits ("
            "id serial PRIMARY KEY, at timestamptz DEFAULT now())"
        )
        conn.execute("INSERT INTO visits DEFAULT VALUES")
        total = conn.execute("SELECT count(*) FROM visits").fetchone()[0]
    return {"visits": total}
