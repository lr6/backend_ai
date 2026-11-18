"""
第四阶段 · 阶段项目 · Task 1A — config.py
配置集中：环境变量只在这一处读取，其它模块 import 这里。

为什么要单独一个 config.py？
  - 数据库地址、Redis 地址、密钥散落在各处 → 换一个环境要翻遍代码
  - 第三阶段 security.py 里 SECRET_KEY 硬编码在源码里，这是生产事故隐患
  - 同一份代码要能跑在 dev / test / prod，差异只应该来自环境变量

依赖方向：config.py 是依赖树的根，不 import 项目里任何其它模块。

写完后运行: ../../.venv/bin/python config.py
全部通过 = Task 1A 的 config 部分 ✅
"""

import os

# TODO 1：DATABASE_URL
#   从环境变量 "DATABASE_URL" 读，读不到用默认值 "postgresql+psycopg:///eng_todo_db"
#   提示：os.getenv(名字, 默认值)
DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg:///eng_todo_db")

# TODO 2：REDIS_URL
#   从环境变量 "REDIS_URL" 读，默认 "redis://127.0.0.1:6379/0"
#   末尾的 0 是 Redis 的 db 编号（学习项 16 练习用的是 15，生产用 0）。
#   不同用途分不同 db，互不干扰。
REDIS_URL: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

# TODO 3：SECRET_KEY
#   从环境变量 "SECRET_KEY" 读，默认 "dev-only-secret-change-me"
#   默认值只给本地开发用 —— 部署时环境里必须设置真实密钥。
SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-only-secret-change-me")


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    import importlib

    errors = []

    def check(name, cond, detail=""):
        if cond:
            print(f"✅ {name}")
        else:
            errors.append(f"{name} {detail}")

    if not isinstance(DATABASE_URL, str):
        errors.append(f"DATABASE_URL 是字符串 实际 {type(DATABASE_URL).__name__}（TODO 1 还没写？）")
    else:
        check("DATABASE_URL 是字符串", True)
        check("DATABASE_URL 默认指向 eng_todo_db",
              DATABASE_URL.endswith("/eng_todo_db"), f"实际 {DATABASE_URL!r}")
        check("DATABASE_URL 使用 psycopg 驱动",
              DATABASE_URL.startswith("postgresql+psycopg://"), f"实际 {DATABASE_URL!r}")

    if not isinstance(REDIS_URL, str):
        errors.append(f"REDIS_URL 是字符串 实际 {type(REDIS_URL).__name__}（TODO 2 还没写？）")
    else:
        check("REDIS_URL 是字符串", True)
        check("REDIS_URL 格式正确",
              REDIS_URL.startswith("redis://") and REDIS_URL.rstrip("/").rsplit("/", 1)[-1].isdigit(),
              f"实际 {REDIS_URL!r}（应为 redis://host:port/db）")

    check("SECRET_KEY 非空", isinstance(SECRET_KEY, str) and len(SECRET_KEY) > 0)

    # ---------- 环境变量覆盖测试 ----------
    # 改了 os.environ 之后，import 过的模块不会自动更新；
    # 用 importlib.reload 让 config.py 重新执行一遍，模拟「进程用新环境变量启动」。
    old_db = os.environ.get("DATABASE_URL")
    old_redis = os.environ.get("REDIS_URL")
    old_secret = os.environ.get("SECRET_KEY")
    try:
        os.environ["DATABASE_URL"] = "postgresql+psycopg:///tmp_custom_db"
        os.environ["REDIS_URL"] = "redis://redis-host:6380/3"
        os.environ["SECRET_KEY"] = "from-env"
        reloaded = importlib.reload(importlib.import_module("config"))

        check("环境变量能覆盖 DATABASE_URL",
              reloaded.DATABASE_URL == "postgresql+psycopg:///tmp_custom_db",
              f"实际 {reloaded.DATABASE_URL!r}")
        check("环境变量能覆盖 REDIS_URL",
              reloaded.REDIS_URL == "redis://redis-host:6380/3",
              f"实际 {reloaded.REDIS_URL!r}")
        check("环境变量能覆盖 SECRET_KEY",
              reloaded.SECRET_KEY == "from-env",
              f"实际 {reloaded.SECRET_KEY!r}")
    finally:
        for key, old in (("DATABASE_URL", old_db), ("REDIS_URL", old_redis), ("SECRET_KEY", old_secret)):
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old
        importlib.reload(importlib.import_module("config"))

    print()
    if errors:
        print(f"有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("🎉 全部通过！Task 1A config.py = ✅")
