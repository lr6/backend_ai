# 第四阶段 · 阶段项目：工程化 Todo API

> 把第三阶段的「认证 Todo API」升级成一个能上线的工程。
> 串联第四阶段 5 个知识点：Redis 缓存、pytest、httpx 集成测试、Nginx、CI/CD。

---

## 任务清单

| Task | 内容 | 状态 |
|------|------|------|
| 1A | **config.py + database.py** — 配置集中、连接 eng_todo_db | ✅ |
| 1B | **业务模块拆包** — models / schemas / security / Alembic 建表 | ✅ |
| 1C | **依赖与路由拆分** — deps.py + routers/ + main.py 组装 | ✅ |
| 2 | **Redis 缓存层** — cache.py + Cache-Aside + 写时删缓存 + 哨兵 | ✅ |
| 3 | **pytest 测试体系** — 独立测试库、Redis db=14、认证 fixture | ✅ |
| 4 | **Nginx 反向代理** — /api 转发、SPA 兜底、upstream 双实例 | ⬜ |
| 5 | **CI/CD** — GitHub Actions 起 PostgreSQL + Redis service 跑测试 | ⬜ |

## 目录结构（目标）

```
config.py           环境变量集中读取
database.py         engine / SessionLocal / Base / get_db
models.py           User / Todo
schemas.py          Pydantic 请求/响应模型
security.py         密码哈希 + JWT
deps.py             get_current_user 等 FastAPI 依赖
routers/
  auth.py           注册 / 登录 / 刷新
  todos.py          todo CRUD（Task 2 接入缓存）
cache.py            Redis 缓存层（Task 2）
main.py             组装 app + include_router
alembic/            数据库迁移
tests/              pytest（Task 3）
nginx/nginx.conf    Nginx 配置（Task 4）
```

## 运行

```bash
# 所有命令在项目根目录（backend_ai）下执行
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/config.py"
.venv/bin/python "4工程化/阶段项目-工程化TodoAPI/database.py"
```

## 与第三阶段项目的关系

代码从 `3认证安全/阶段项目-认证TodoAPI/` **复制并改造**：

- 数据库：`auth_todo_db` → `eng_todo_db`
- `SECRET_KEY`：从硬编码 → `config.py` 读环境变量
- 单文件 `main.py` → 按职责拆包
- 新增：缓存层、测试体系、Nginx、CI
