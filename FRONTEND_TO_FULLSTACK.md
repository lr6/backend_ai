# 🚀 前端转全栈：Python + FastAPI 学习路径

> 基于 [Backend Developer Roadmap 2026](BACKEND_ROADMAP_2026.md) 裁剪
> 目标用户：前端开发者（已掌握 HTML/CSS/JS/Git/HTTP 基础）
> 推荐后端语言：**Python** + **FastAPI**

---

## ✅ 你已经会的（可以直接跳过）

| 模块 | 你已有的前端知识 | 路线图对应 |
|------|-----------------|-----------|
| Internet 基础 | HTTP、DNS、浏览器原理 | Introduction ✅ |
| 版本控制 | Git、GitHub | Version Control Systems ✅ |
| 前端基础 | HTML、CSS、JavaScript | Frontend Basics ✅ |
| API 消费 | 你一定调过无数 REST API | API 概念有基础 ✅ |
| AI 工具 | Copilot、Cursor 等大概率在用 | AI Assisted Coding ✅ |

---

## 🎯 你需要学的（按优先级排序）

### 第零阶段：Python 语言速通（1-2 周）

```
目标：用你已有的 JS 知识为锚点，快速上手 Python
```

| # | 主题 | 学什么 | JS 对照（帮你快速理解） |
|---|------|--------|------------------------|
| 0.1 | **语法基础** | 变量、函数、循环、条件 | `let` → 不需要声明；`function` → `def`；`{}` → 缩进 |
| 0.2 | **数据结构** | list、dict、tuple、set | `Array` → `list`；`Object` → `dict`；多了不可变的 `tuple` |
| 0.3 | **类型提示 (Type Hints)** | `def foo(x: int) -> str:` | 类似 TypeScript，但运行时不管，靠工具检查 |
| 0.4 | **虚拟环境 & 包管理** | `venv`、`pip`、`pyproject.toml` | 相当于 `node_modules` + `package.json`，但隔离方式不同 |
| 0.5 | **异步基础** | `async def`、`await`、`asyncio` | 你写 JS 的 `async/await` 可以直接平移，概念几乎一样 |
| 0.6 | **Pydantic** | 数据校验 + 序列化模型 | 前端的 Zod / Yup，但 Python 里它是 FastAPI 的基石 |

**动手项目**：用纯 Python（不用框架）写一个命令行 Todo 工具，数据存 JSON 文件

> 💡 你不需要把 Python 学到精通。把上面 6 项搞懂，就可以开始写 FastAPI 了，其余边做边查。

---

### 第一阶段：API 设计思维转换（2 周）

```
目标：把"用 API"的思维切换为"写 API"的思维
```

| # | 主题 | 学什么 | 为什么重要 |
|---|------|--------|-----------|
| 1 | **🟣 FastAPI 入门** | 路由、请求体、查询参数、路径参数 | Python 界目前最现代的 Web 框架 |
| 2 | **🟣 REST API 设计** | 资源建模、状态码语义、分页、错误处理 | 从"调接口的"变成"设计接口的" |
| 3 | **🟣 FastAPI 进阶** | 依赖注入（Depends）、中间件、生命周期 | FastAPI 的核心设计模式，不理解就写不好 |
| 4 | **🟣 自动文档** | Swagger UI / ReDoc、OpenAPI 规范 | FastAPI 自带，写完代码就有文档——前端同学会爱上这个 |

**动手项目**：用 FastAPI 写一个 Todo API（CRUD + 数据存内存），访问 `/docs` 看到 Swagger 界面

---

### 第二阶段：数据持久化（2-3 周）

```
目标：理解数据如何存储、查询、建模
```

| # | 主题 | 学什么 | 为什么重要 |
|---|------|--------|-----------|
| 5 | **🟣 PostgreSQL** | SQL 基础、表设计、JOIN、索引 | 后端最核心的技能，没有之一 |
| 6 | **🟣 SQLAlchemy 2.0** | ORM 模型定义、Session、查询 | Python 生态的 ORM 标准，FastAPI 的最佳搭档 |
| 7 | **🟣 Alembic** | 数据库迁移（migration） | 表结构变更的版本控制，相当于前端的 Git，但管的是数据库 schema |
| 8 | **🟣 Transactions** | ACID、事务隔离级别、`session.commit()` | 钱相关的操作必须懂这个 |
| 9 | **🟣 Normalization** | 范式化、反范式化的取舍 | 前端同学最容易设计出烂表结构 |
| 10 | **🟣 N+1 Problem** | `selectinload` / `joinedload`（Eager Loading） | SQLAlchemy 默认 lazy load，一不小心就 1000 次查询 |

**动手项目**：把 Todo API 接入 PostgreSQL，用 SQLAlchemy + Alembic 管理表结构，加上用户表（`users` 1→N `todos`）

---

### 第三阶段：认证与安全（1-2 周）

```
目标：理解登录、权限、安全防护
```

| # | 主题 | 学什么 | 为什么重要 |
|---|------|--------|-----------|
| 11 | **🟣 JWT** | Access Token / Refresh Token、`python-jose` | 现代 API 认证的事实标准 |
| 12 | **🟣 FastAPI OAuth2** | FastAPI 内置的 OAuth2 工具、依赖注入整合 | FastAPI 已经把流程框架搭好了，填逻辑就行 |
| 13 | **🟣 passlib + bcrypt** | 密码哈希、加盐 | 绝不能用明文存密码 |
| 14 | **🟣 CORS** | 跨域原理、`CORSMiddleware` 配置 | 你被 CORS 折磨过，现在要理解它并从服务端正确配置 |
| 15 | **🟣 HTTPS / SSL/TLS** | 证书、加密原理、生产环境配置 | 生产环境必备 |

**动手项目**：给 Todo API 加上注册/登录/JWT 鉴权，每个用户只能操作自己的 todo

---

### 第四阶段：工程化（2-3 周）

```
目标：学会构建生产级后端服务
```

| # | 主题 | 学什么 | 为什么重要 |
|---|------|--------|-----------|
| 16 | **🟣 Redis 缓存** | `redis-py`、缓存策略（Cache-Aside）、失效策略 | 性能优化的核心手段 |
| 17 | **🟣 pytest** | fixture、parametrize、mock | Python 测试的事实标准 |
| 18 | **🟣 httpx + pytest** | API 集成测试、`TestClient` | FastAPI 自带 TestClient，写集成测试非常方便 |
| 19 | **🟣 Nginx** | 反向代理、负载均衡、静态文件 | 你的 uvicorn 前面永远该有个 Nginx |
| 20 | **🟣 CI/CD** | GitHub Actions：lint → test → build → deploy | 代码 push → 自动跑测试 → 自动部署 |

**动手项目**：给 Todo API 加上 Redis 缓存、pytest 测试覆盖 >80%、Nginx 反代、配 GitHub Actions

---

### 第五阶段：架构与系统设计（3-4 周）

```
目标：理解后端架构的全貌
```

| # | 主题 | 学什么 | 为什么重要 |
|---|------|--------|-----------|
| 21 | **🟣 Docker** | Dockerfile、docker-compose、多服务编排 | 告别"在我机器上能跑" |
| 22 | **🟣 Celery + Redis** | 异步任务队列、定时任务 | Python 生态的标准方案，用于发邮件、生成报表等后台任务 |
| 23 | **🟣 Monolith vs Microservices** | 两种架构的优劣、何时该拆 | 不要一上来就微服务 |
| 24 | **🟣 Database Indexes** | B-Tree、复合索引、`EXPLAIN ANALYZE` | 慢查询排查必备 |
| 25 | **🟣 MongoDB** | 文档型数据库、何时用 NoSQL（`motor` 异步驱动） | 不是所有数据都适合关系型 |
| 26 | **🟣 WebSockets** | FastAPI WebSocket、实时通信 | 前端 WebSocket 你会用，现在学服务端实现 |

**动手项目**：Todo 应用升级为实时协作版（WebSocket），后台任务用 Celery（到期提醒），全部 Docker 化

---

### 第六阶段：生产就绪（持续学习）

```
目标：达到能独立负责后端服务的水平
```

| # | 主题 | 学什么 | 为什么重要 |
|---|------|--------|-----------|
| 27 | **🟣 structlog** | 结构化日志、日志级别、上下文 | `print()` 不是日志 |
| 28 | **🟣 Prometheus + Grafana** | Metrics、监控面板 | 知道服务是死是活、快还是慢 |
| 29 | **🟣 Circuit Breaker** | 熔断、降级、重试策略（`tenacity`） | 微服务调用链的保险丝 |
| 30 | **🟣 Rate Limiting** | 限流算法（`slowapi`） | 防止接口被刷爆 |
| 31 | **🟣 Kubernetes** | Pod、Service、Deployment 基础 | Docker 的下一个台阶 |
| 32 | **🟣 System Design** | 设计 Twitter/URL Shortener/聊天系统 | 面试必考 + 实际必用 |

---

## 📊 学习时间估算

| 阶段 | 内容 | 预估时间 | 累计 |
|------|------|---------|------|
| 零 | Python 语言速通 | 1-2 周 | 2 周 |
| 一 | API 设计思维转换 | 2 周 | 4 周 |
| 二 | 数据库 | 2-3 周 | 7 周 |
| 三 | 认证安全 | 1-2 周 | 9 周 |
| 四 | 工程化 | 2-3 周 | 12 周 |
| 五 | 架构设计 | 3-4 周 | 16 周 |
| 六 | 生产就绪 | 持续 | — |

> ⏱️ **总计：约 4 个月**可以达到独立开发后端服务 + 部署上线的水平（每天投入 2-3 小时）。
> 比 Node.js 路线多 2-4 周，多出来的时间主要花在 Python 语言本身。

---

## 🎯 核心原则

1. **Python 只是工具，后端思维才是目的** — 不要把时间花在成为 Python 专家上，够用就行
2. **每个阶段必做项目** — 前端转后端最大的障碍不是语法，是思维模式的切换。只有写代码才能完成这个切换
3. **🟣 优先，🟢 了解即可** — 时间有限，先学推荐项，备选项知道是干什么的就行
4. **从单体开始** — 不要一上来就微服务，一个人写微服务是给自己找麻烦
5. **数据库是核心** — 大部分前端转后端的短板都是数据库设计，花最多时间在上面
6. **善用 FastAPI 的自动文档** — `/docs` 是你最直观的调试工具，也是前后端协作的契约

---

## 🔗 推荐资源

| 主题 | 资源 |
|------|------|
| Python 入门 | [Python Official Tutorial](https://docs.python.org/3/tutorial/) |
| FastAPI | [FastAPI 官方文档](https://fastapi.tiangolo.com/)（写得极好，直接看） |
| Pydantic | [Pydantic Docs](https://docs.pydantic.dev/) |
| SQLAlchemy 2.0 | [SQLAlchemy 2.0 Tutorial](https://docs.sqlalchemy.org/en/20/tutorial/) |
| Alembic | [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html) |
| PostgreSQL | [PostgreSQL Tutorial](https://www.postgresqltutorial.com/) |
| pytest | [pytest 官方文档](https://docs.pytest.org/) |
| Redis | [Redis University](https://redis.io/university/) |
| Celery | [Celery 文档](https://docs.celeryq.dev/) |
| Docker | [Docker 从入门到实践](https://docker-practice.github.io/) |
| System Design | [System Design Primer](https://github.com/donnemartin/system-design-primer) |
| 完整路线图 | [Backend Roadmap 2026](BACKEND_ROADMAP_2026.md) |

---

> 💡 **一句话总结**：你不需要学完路线图上的每一项。先搞定 **Python 基础 + FastAPI + PostgreSQL + Docker 部署**，这四个掌握了，你就已经有能力独立构建和部署一个完整的全栈应用。其他的（Redis、Celery、K8s）在实践中逐步补进来。
