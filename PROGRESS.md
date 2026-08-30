# 📊 学习进度追踪

> **单一真相来源** — 所有学习进度记录在此。
> 每次学习会话结束后必须更新此文件。
> Claude 打开项目时首先读取此文件。

---

## 🟢 当前状态

| 项目 | 值 |
|------|-----|
| **当前阶段** | 第二阶段：数据持久化 |
| **当前学习项** | 9 Normalization（⬜ 未开始）|
| **总进度** | 14 / 32 |
| **已完成阶段** | 第零阶段 ✅、第一阶段 ✅ |
| **最近学习日期** | 2026-08-30 |
| **最近学习内容** | 8 Transactions（7 练习全通，学习项 8 完成）|

---

## 📋 学习进度明细

### 第零阶段：Python 语言速通（1-2 周）

| # | 状态 | 学习项 | 完成日期 | 笔记 |
|---|------|--------|---------|------|
| 0.1 | ✅ | **语法基础** — 变量、函数、循环、条件 | 2026-08-11 | f-string、缩进、切片、list/dict 基础操作 |
| 0.2 | ✅ | **数据结构** — list、dict、tuple、set | 2026-08-12 | 列表/字典推导式、切片、tuple解包、set交集、dict.get() 安全访问 |
| 0.3 | ✅ | **类型提示 (Type Hints)** — `def foo(x: int) -> str` | 2026-08-12 | str \| None、list[int]、TypedDict、Callable、类型别名 |
| 0.4 | ✅ | **虚拟环境 & 包管理** — venv、pip、pyproject.toml | 2026-08-12 | venv创建/激活、pip install、requirements.txt、pyproject.toml、sys.prefix检测 |
| 0.5 | ✅ | **异步基础** — async/await、asyncio | 2026-08-13 | async/await、gather 并发、create_task、asyncio.run 入口 vs await、gather(*arr) 解包 |
| 0.6 | ✅ | **Pydantic** — 数据校验与序列化 | 2026-08-13 | BaseModel、ValidationError、coercion、Field 约束、model_dump、嵌套模型 |

> 🛠️ 阶段项目：用纯 Python（不用框架）写一个命令行 Todo 工具

| 阶段项目 | 状态 | 完成日期 |
|----------|------|---------|
| CLI Todo 工具 | ✅ | 2026-08-14 |

---

### 第一阶段：API 设计思维转换（2 周）

| # | 状态 | 学习项 | 完成日期 | 笔记 |
|---|------|--------|---------|------|
| 1 | ✅ | **FastAPI 入门** — 路由、请求体、查询参数、路径参数 | 2026-08-24 | 路由/路径参数/查询参数/请求体 + TestClient；踩坑：字段写成嵌套 class |
| 2 | ✅ | **REST API 设计** — 资源建模、状态码、分页、错误处理 | 2026-08-24 | in 方向/return 位置/状态码 vs body/dict[] vs 对象./return vs raise |
| 3 | ✅ | **FastAPI 进阶** — Depends、中间件、生命周期 | 2026-08-24 | Depends=Hook、中间件=拦截器、lifespan=yield 分界 |
| 4 | ✅ | **自动文档** — Swagger UI、OpenAPI 规范 | 2026-08-24 | Swagger UI=Postman、openapi.json=契约、模型被引用才进文档 |

> 🛠️ 阶段项目：用 FastAPI 写一个 Todo API（CRUD + 数据存内存）

| 阶段项目 | 状态 | 完成日期 |
|----------|------|---------|
| FastAPI Todo API | ✅ | 2026-08-24 |

---

### 第二阶段：数据持久化（2-3 周）

| # | 状态 | 学习项 | 完成日期 | 笔记 |
|---|------|--------|---------|------|
| 5 | ✅ | **PostgreSQL** — SQL 基础、表设计、JOIN、索引 | 2026-08-25 | SQL CRUD ✅、表设计 ✅、JOIN ✅、索引 ✅ |
| 6 | ✅ | **SQLAlchemy 2.0** — ORM 模型定义、Session、查询 | 2026-08-27 | Mapped/mapped_column=2.0、select构造≠执行、session.get特例、relationship两端镜像、属性名是契约、default兜非空 |
| 7 | ✅ | **Alembic** — 数据库迁移 | 2026-08-30 | 迁移=数据库的Git、autogenerate差异驱动、down_revision迁移链、downgrade回滚、alembic_version版本跟踪 |
| 8 | ✅ | **Transactions** — ACID、事务隔离级别 | 2026-08-30 | 原子性=commit/rollback 打包、隔离级别快照、FOR UPDATE 锁到事务结束 |
| 9 | ⬜ | **Normalization** — 范式化与反范式化 | — | — |
| 10 | ⬜ | **N+1 Problem** — selectinload / joinedload | — | — |

> 🛠️ 阶段项目：Todo API 接入 PostgreSQL，SQLAlchemy + Alembic，加上用户表

| 阶段项目 | 状态 | 完成日期 |
|----------|------|---------|
| PostgreSQL Todo API | ⬜ | — |

---

### 第三阶段：认证与安全（1-2 周）

| # | 状态 | 学习项 | 完成日期 | 笔记 |
|---|------|--------|---------|------|
| 11 | ⬜ | **JWT** — Access Token / Refresh Token、python-jose | — | — |
| 12 | ⬜ | **FastAPI OAuth2** — 依赖注入整合 | — | — |
| 13 | ⬜ | **passlib + bcrypt** — 密码哈希、加盐 | — | — |
| 14 | ⬜ | **CORS** — 跨域原理、CORSMiddleware | — | — |
| 15 | ⬜ | **HTTPS / SSL/TLS** — 证书、加密原理 | — | — |

> 🛠️ 阶段项目：Todo API 加上注册/登录/JWT 鉴权

| 阶段项目 | 状态 | 完成日期 |
|----------|------|---------|
| 认证 Todo API | ⬜ | — |

---

### 第四阶段：工程化（2-3 周）

| # | 状态 | 学习项 | 完成日期 | 笔记 |
|---|------|--------|---------|------|
| 16 | ⬜ | **Redis 缓存** — redis-py、缓存策略 | — | — |
| 17 | ⬜ | **pytest** — fixture、parametrize、mock | — | — |
| 18 | ⬜ | **httpx + pytest** — API 集成测试、TestClient | — | — |
| 19 | ⬜ | **Nginx** — 反向代理、负载均衡、静态文件 | — | — |
| 20 | ⬜ | **CI/CD** — GitHub Actions | — | — |

> 🛠️ 阶段项目：Todo API + Redis 缓存 + Nginx + 测试 + CI/CD

| 阶段项目 | 状态 | 完成日期 |
|----------|------|---------|
| 工程化 Todo API | ⬜ | — |

---

### 第五阶段：架构与系统设计（3-4 周）

| # | 状态 | 学习项 | 完成日期 | 笔记 |
|---|------|--------|---------|------|
| 21 | ⬜ | **Docker** — Dockerfile、docker-compose | — | — |
| 22 | ⬜ | **Celery + Redis** — 异步任务队列 | — | — |
| 23 | ⬜ | **Monolith vs Microservices** — 架构取舍 | — | — |
| 24 | ⬜ | **Database Indexes** — B-Tree、EXPLAIN ANALYZE | — | — |
| 25 | ⬜ | **MongoDB** — 文档型数据库、motor 驱动 | — | — |
| 26 | ⬜ | **WebSockets** — FastAPI WebSocket | — | — |

> 🛠️ 阶段项目：Todo 实时协作版（WebSocket），后台任务 Celery，Docker 化

| 阶段项目 | 状态 | 完成日期 |
|----------|------|---------|
| 实时协作 Todo | ⬜ | — |

---

### 第六阶段：生产就绪（持续）

| # | 状态 | 学习项 | 完成日期 | 笔记 |
|---|------|--------|---------|------|
| 27 | ⬜ | **structlog** — 结构化日志 | — | — |
| 28 | ⬜ | **Prometheus + Grafana** — Metrics、监控面板 | — | — |
| 29 | ⬜ | **Circuit Breaker** — 熔断、降级、重试 | — | — |
| 30 | ⬜ | **Rate Limiting** — 限流算法、slowapi | — | — |
| 31 | ⬜ | **Kubernetes** — Pod、Service、Deployment | — | — |
| 32 | ⬜ | **System Design** — 设计经典系统 | — | — |

> 第六阶段无独立项目，在实际项目中逐步引入这些能力。

---

## 📝 学习日志

<!-- 每次会话结束后，在此记录关键收获和遇到的问题 -->

| 日期 | 学习项 | 关键收获 / 问题 |
|------|--------|----------------|
| 2026-08-11 | 0.1 语法基础 | 6个练习全部通过；踩坑：f-string 忘加 f、for in 遍历了 range 而不是参数 |
| 2026-08-12 | 0.2 数据结构 | 7个练习全部通过；踩坑：range(n) 从 0 开始忘写起始值、range(1, n) 不包含 n |
| 2026-08-12 | 0.3 类型提示 | 7个练习全部通过；踩坑：浮点数精度问题，用 round() 保留两位小数；TypedDict vs 普通 dict 的区别 |
| 2026-08-12 | 0.4 虚拟环境 & 包管理 | 5个练习全部通过；踩坑：Git Bash 下 source activate 不生效，改用 .venv/Scripts/python.exe 直接调用；and/or 逻辑写反；'None'（字符串）vs None |
| 2026-08-13 | 0.5 异步基础 | 6个练习全部通过；踩坑：asyncio.run 在协程内报 RuntimeError 应改用 await；gather(arr) 要 * 展开；asyncio.sleep 单位是秒 |
| 2026-08-13 | 0.6 Pydantic | 7个练习全部通过；踩坑：ValidationError 要 try/except 捕获否则程序崩溃；validate_age 与 negative_price_raises 的 True/False 语义相反 |
| 2026-08-14 | 阶段项目 CLI Todo | 4 命令全通；踩坑：json.dump 参数顺序反、w 模式读空文件报错、f-string 硬编码"标题"、delete 漏 save 只改内存没持久化 |
| 2026-08-24 | 1 FastAPI 入门 | 4 练习全通；踩坑：Pydantic 字段写成了嵌套 class 导致 AttributeError，字段应直接写在类体里 |
| 2026-08-24 | 2 REST API 设计 | 4 练习全通；踩坑：in 方向搞反、return 写循环里、状态码塞 body（犯 2 次）、dict 用点访问、return 当 raise 用 |
| 2026-08-24 | 3 FastAPI 进阶 | 3 练习一次全通无踩坑；Depends=依赖注入、中间件=拦截器、lifespan=yield 分界线 |
| 2026-08-24 | 4 自动文档 | 4 练习全通；踩坑：参数缺逗号、title 拼成 titlle、模型没被路由引用不进文档 |
| 2026-08-24 | 阶段项目 FastAPI Todo API | 18 测试全通；踩坑：JS 思维混入（splice/enumerate/三元）、id 塞进请求体模型、路径参数缺 :int |
| 2026-08-24 | 5 PostgreSQL（SQL 基础） | 6 练习全通；踩坑：SQL 当 Python 代码写（没引号/没 conn.execute）、execuye/NSERT 拼写、return cur 忘 fetchall |
| 2026-08-24 | 5 PostgreSQL（表设计） | 6 练习全通；踩坑：INTERGE 拼写、INSERT 缺 RETURNING id、SELECT 缺 WHERE、fetchone()[0] vs fetchone()、sername/(username) 缺逗号 |
| 2026-08-25 | 5 PostgreSQL（JOIN） | 6 练习全通；踩坑：`==` 当 SQL 相等、ORDER BY ASC 语序、fetchall 直接 return 忘列表推导、username 反复拼错、GROUP BY 规则（u.id 没进分组键）|
| 2026-08-25 | 5 PostgreSQL（索引） | 6 练习全通，学习项 5 完成；踩坑：pg_index 拼错（应 pg_indexes）、CREATE 漏 INDEX、arr.join(',') 方向写反（JS 数组方法 vs Python 字符串方法）、fetchall 忘列表推导（第 3 次）|
| 2026-08-27 | 6 SQLAlchemy 2.0 | 7 练习全通，学习项 6 完成；踩坑：select 构造≠执行（Select no attr / 反复）、count 缺 select_from+scalar、session.get 误 execute、commit(user) 传参、scalars() 挂 select、top 缺 .all()、done 非空需 default、relationship 只写一端忘 import、改名 rela_ 违反契约 |
| 2026-08-28 | 7 Alembic（进行中）| 配置完成（alembic.ini URL + env.py target_metadata + models.py）；踩坑：Todo 漏 __tablename__（InvalidRequestError）、macOS venv 路径是 bin/ 不是 Scripts/、autogenerate 生成空迁移（数据库已有 create_all 建的表，差异驱动无差异）；中断点见 07Alembic/学习进度快照.md |
| 2026-08-30 | 7 Alembic | 7 练习全通，学习项 7 完成；新建练习库 alembic_practice_db（不动 todo_orm_db），从零走通完整迁移：autogenerate 生成 create_table → upgrade → psql 验证 + alembic current；改模型加 due_date（Mapped[date | None] → nullable=True，sa.Date() 由类型注解自动推断）→ 第二个迁移（down_revision 成链）；downgrade -1 回滚验证列消失再恢复；history/current 看历史。踩坑核心：空迁移=无差异，autogenerate 是差异驱动 |
| 2026-08-30 | 8 Transactions | 7 练习全通，学习项 8 完成；新建练习库 transaction_practice_db。核心概念：ACID、READ COMMITTED vs REPEATABLE READ 快照、FOR UPDATE 行锁（锁到事务结束）。踩坑：return 当 raise（第 2 次）、execcute/execcute 拼写（第 N 次）、SQL 字符串缺引号/表名拼错 account、字符串拼接缺空格、**中文输入法弯引号 ‘ ’ 导致 unterminated quoted string**、VALUES 里逗号被引号包住、conn_b 不 commit 读不到修改、自己连接读自己未提交的改动不是脏读（要用另一个连接）、FOR UPDATE 后立刻 commit 锁提前释放 |

---

## 🔄 进度更新规则

1. **开始学一项**：将 ⬜ 改为 🔄
2. **完成一项**：将 🔄 改为 ✅，填写完成日期
3. **阶段项目完成**：在阶段项目表中标记 ✅
4. **更新「当前状态」表**：每次会话结束前更新当前阶段、当前学习项、总进度
5. **写学习日志**：至少写一行，记录今天的收获
