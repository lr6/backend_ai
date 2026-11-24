# 第五阶段 · 21 Docker — 学习笔记

> 2026-11-24 学习项 21 Docker ✅
> 练习环境：`5架构设计/21Docker/`（`app/` 微型 FastAPI 服务 + `check.py` 自动验证）
> 最终产出：`app/Dockerfile`、`app/.dockerignore`、`docker-compose.yml`（app + postgres + redis 三服务编排）

---

## 一、知识点讲解

### 1. Docker 要解决什么

不加 Docker 时，把 `4工程化/阶段项目-工程化TodoAPI` 跑起来要手做 6 步：

```
1. cd 项目 && source .venv/bin/activate
2. pip install -r requirements.txt
3. 本机 PostgreSQL 起着、建好库
4. 本机 Redis 起着
5. alembic upgrade head
6. uvicorn main:app --port 8001（再起一个 8002）
```

换台机器（同事 / CI / 服务器）全部重来，版本差一点就「在我机器上能跑」。Docker 把这些步骤连同**环境本身**打包进镜像，一条命令重建。

### 2. 镜像 image / 容器 container / 虚拟机 VM

| 概念 | 是什么 | 前端类比 |
|------|--------|---------|
| Dockerfile | 构建说明书 | `vite.config.js` + `package.json` |
| 镜像 image | 只读的完整环境快照（OS 基础层 + Python + 代码 + 依赖） | `npm run build` 出的 `dist/` |
| 容器 container | 镜像跑起来的实例，一个镜像能起 N 个 | 用 `dist/` 起的 nginx 进程 |
| docker-compose | 多服务的编排文件 | 一份「同时起哪些服务、怎么连」的说明 |

容器 vs 虚拟机：

| | VM | 容器 |
|---|---|---|
| 打包内容 | 一整套 guest OS（含内核） | 只有应用 + 依赖，**共用宿主内核** |
| 体积 | 几 GB | 几十 MB ~ 几百 MB |
| 启动 | 几十秒 | 毫秒 ~ 秒级 |
| 隔离 | 硬件级 | 进程级 |

一句话：**VM 是虚拟出一台新电脑，容器是虚拟出一套环境但共用你的内核。**

### 3. 只读层 + 可写层（写时复制）

镜像由多层只读层叠加而成（Dockerfile 每条指令产出一层）。容器启动时在最上面加一层**可写层**：

```
┌──────────────────────────────┐
│ 容器可写层（运行时改动）          │ ← docker run 之后才有，容器删除即销毁
├──────────────────────────────┤
│ 你的代码（COPY . .）           │
│ 依赖（RUN pip install ...）    │ 镜像层，只读，多容器共享
│ 基础镜像 python:3.12-slim      │
└──────────────────────────────┘
```

**关键分界线**：同一条 `pip install`，在哪个时机执行，结果去向完全不同。

| 时机 | 写到哪 | 删容器后 | 其他容器可见 |
|---|---|---|---|
| `docker build`（Dockerfile 的 `RUN`） | 镜像新层（只读） | ✅ 还在 | ✅ |
| `docker run` 之后（`docker exec` 手敲） | 容器可写层 | ❌ 没了 | ❌ |

所以「进容器手动装包修好了」是 Docker 里最常见的坏习惯 —— 一重建就没了。**依赖必须写进 Dockerfile。**

同理，运行时的数据（数据库文件）也不能留在容器里，要用 **volume**。

### 4. 常用命令

| 命令 | 作用 |
|------|------|
| `docker run <镜像>` | 从镜像起容器（本地没有就去 Docker Hub 拉） |
| `docker run -d --name web -p 8080:80 nginx` | 后台跑 + 命名 + 端口映射 |
| `docker ps` / `docker ps -a` | 运行中 / 全部（含已退出） |
| `docker logs <容器>` | 容器输出 |
| `docker exec -it <容器> bash` | 进入运行中的容器 |
| `docker stop` / `docker rm -f` | 停 / 强删 |
| `docker images` | 本地镜像列表 |
| `docker build -t 名字 目录` | 按 Dockerfile 构建镜像 |
| `docker compose up -d --build` | 编排启动（构建 + 后台） |
| `docker compose ps` / `logs -f app` / `exec postgres psql ...` | 看状态 / 看日志 / 进服务 |
| `docker compose down` / `down -v` | 停并删容器（保留卷）/ 连卷一起删 |

### 5. 端口映射 `-p 宿主机:容器`

```
-p 8080:80     # Mac 的 8080 → 容器的 80
```

- 容器有自己的网络命名空间，不映射的话宿主机根本访问不到
- `0.0.0.0:8080->80/tcp` 里的 `0.0.0.0` = 所有网卡，局域网设备也能访问
- 写 `-p 127.0.0.1:8080:80` 则只绑本机回环，别人访问不到
- **容器之间互相访问不需要 `ports`**，用容器端口（如 `postgres:5432`）即可

### 6. Dockerfile 六行 + 构建缓存

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

- `--host 0.0.0.0` 不能省：默认绑 `127.0.0.1` 只在容器内可达，`-p` 映射也白搭（同 Vite `--host`）
- `CMD` 用 **JSON 数组形式**：`["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]`
- `--no-cache-dir`：pip 默认把 wheel 缓存在镜像里（`/root/.cache/pip`），运行时用不上，白占空间

**为什么要两次 COPY**：缓存 key = 上一层内容 + 指令 + 指令涉及的文件内容；一层变了后面全部重建。

| 写法 | 只改 `app.py` 时 rebuild | `pip install` 层 |
|---|---|---|
| 先 `COPY requirements.txt` 再装（✅ 本练习） | `COPY . .` 重跑 **0.0s** | `CACHED` 跳过 |
| 先 `COPY . .` 再装（❌） | `COPY . .` → `RUN pip install` **重跑 17.7s** | 每次从零装 |

实测数据（同机、同依赖）：

```
# 正确顺序，改代码后：
#7 [3/5] COPY requirements.txt .    → CACHED
#8 [4/5] RUN pip install ...        → CACHED
#9 [5/5] COPY . .                   → DONE 0.0s

# 错误顺序，改代码后：
#7 [3/4] COPY . .                   → DONE 0.1s
#8 [4/4] RUN pip install ...        → DONE 17.7s
```

规律：**越少变的指令放越前，越多变的放越后**。

### 7. `.dockerignore`

写法同 `.gitignore`。`COPY . .` 会拷目录里的一切，但这些东西不该进镜像：

- `__pycache__/`、`.pytest_cache/`、`.ruff_cache/` —— 本机产物
- `.git/` —— 体积大，镜像里没用
- `.env` —— **密钥泄露**，镜像可能被推送分享
- `.venv/` —— 本机编译的二进制，架构可能不对（Mac ARM vs Linux 镜像）

注意：**镜像分层，后面一层删掉前一层仍能看到文件**。所以 `.env` 必须被 ignore，不能「先拷进去再删」。

### 8. docker-compose

顶层结构：`services`（要跑的容器）+ `volumes`（命名卷），`networks` 默认自动创建。

每个 service 常用字段：

| 字段 | 作用 |
|------|------|
| `image` / `build` | 二选一：用现成镜像 / 从 Dockerfile 构建 |
| `ports` | 宿主机 → 容器映射，**只有要从外面访问时才写** |
| `environment` | 环境变量 |
| `volumes` | 挂载（数据库数据必须挂） |
| `depends_on` | 启动顺序 |
| `healthcheck` | 判断服务是否真的就绪 |

**服务名就是内网 DNS 主机名**：

```
DATABASE_URL: postgresql://todo:todo@postgres:5432/todo
                                    ↑ 服务名，不是 localhost
REDIS_URL: redis://redis:6379/0
```

**健康检查 + 依赖顺序**（关键坑）：

```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U todo"]
  interval: 5s
  timeout: 3s
  retries: 10
depends_on:
  postgres:
    condition: service_healthy
```

`depends_on: [postgres]` 只保证「进程起来了」，PG 起来后还要几秒初始化才接受连接；`service_healthy` 才是「能用了」。这类问题本地偶发、CI 必现。

**为什么数据库不装进 app 容器**：一个容器一个职责。独立升级、独立重启、独立扩缩容、数据卷独立；绑一起的话改一行 Python 就得重建整个数据库环境。

### 9. 命名卷：数据活过容器

```yaml
services:
  postgres:
    volumes:
      - pgdata:/var/lib/postgresql/data
volumes:
  pgdata:
```

- `docker compose down` → 删容器，**卷保留** → 数据还在
- `docker compose down -v` → 连卷一起删 → 数据清空

### 10. YAML 语法三条铁律（本练习踩过）

1. 键值必须 `键: 空格 值` —— `build ./app` ❌ → `build: ./app` ✅
2. 列表项用 `- ` 开头，不能只写键名 —— `ports` ❌ → `ports:` + `- "8090:8000"` ✅
3. 缩进必须一致，不能用 Tab（同 Nginx / GitHub Actions 的 YAML 坑）

---

## 二、练习 ↔ 知识点映射

| 练习 | 文件 | 对应知识点 |
|------|------|-----------|
| 练习 1：写 Dockerfile | `app/Dockerfile` | §2 镜像/容器、§6 六行结构与缓存、§5 端口 |
| 练习 1 追加：`--no-cache-dir`、`.dockerignore` | `app/.dockerignore` | §7 |
| 练习 2：写 docker-compose.yml | `docker-compose.yml` | §8 compose、§9 命名卷、§4 命令 |

`check.py` 用法：

```
python3 check.py            # 练习 1
python3 check.py --part2    # 练习 2
python3 check.py --all      # 两个都跑
```

练习 1 验证：build 成功 → 容器 Up → `/greeting` 返回 → `/health` app=ok
练习 2 验证：三服务起 → `.dockerignore` 生效（本机假 `__pycache__` 未进镜像）→ db/redis up（服务名解析）→ 环境变量传入 → 能写 PG → `down`/`up` 后数据还在（volume）

---

## 三、练习纠错全记录

### 探底（讲解前）

**Q1：现在要把项目跑起来，手头要做哪些步骤？**
答：「直接 docker 启动」。
→ 项目里其实**没有** Dockerfile / compose，`docker start` 无从下手。用户对「配置步骤」无概念，只记着 Docker 能起容器。后来讲解 + 列出真实 6 步手动流程补齐。

**Q2：镜像和容器什么关系？容器和 VM 有什么区别？**
答：「我不知道」→ 从零讲。

### 误区 1：「容器里 pip install 会写进镜像」

检查题：容器里 `pip install` 装的包会进镜像吗？
答：「会的，这属于依赖吗」→ 错。
用户随后**主动提问**：「已装的依赖和容器可写层，这不矛盾吗？我一会在一会不在」—— 说明「分层」和「时机」两个概念没绑定。
→ 讲清分界线：`docker build`（Dockerfile 的 RUN）产物进镜像；`docker run` 之后手敲的进可写层。
→ 检查题 A/B（Dockerfile 里装 vs 容器里装，删容器后还在吗）答对：「a 在 b 不在」。

### 验证实验：容器改动不会回写镜像

`docker exec web sh -c "echo '<h1>被改过了</h1>' > /usr/share/nginx/html/index.html"` → curl 看到「被改过了」→ `docker rm -f web` → 新起容器 → Welcome 页回来。
预测正确：「welcome，因为改的是可写层，容器删了可写层就没了」。

### 误区 2：`localhost:80` 能不能访问 `-p 8080:80` 的 nginx

答：「不能，我得打开 8080 才行」✅

### 检查题：Dockerfile 里把 `COPY . .` 挪到 `RUN pip install` 前面

答：「能跑，我不知道为啥实践中不这么写」→ 直接讲缓存。
用实测数据补强（见 §6）：正确顺序改代码 0.0s，错误顺序 17.7s。

### `.env` 被拷进镜像的后果

答：「直接暴露我们的密钥」✅
补充：分层导致即使后续层删除，前面层的文件仍可从镜像历史中取出。

### 练习 1 实操

用户独立写完 Dockerfile，**一次通过**（build + Up + `/greeting` + `/health` 全绿）。
Review 建议三处：`--no-cache-dir`、`.dockerignore`、清理脚手架注释。用户全部照改。

### 误区 3：容器里 `localhost` 能连本地 PG

探底：app 装进容器后 `DATABASE_URL` 里的 `localhost` 还能用吗？
答：「我觉得应该可以吧，容器也会安装 pg 的。localhost 代表容器。」
→ 一半对：`localhost` 确实指容器自己；但**不会**把 PG 装进 app 容器，所以连不上。
→ 讲「一个容器一个职责」+ compose 内网 DNS（服务名 = 主机名）+ 容器间通信不需要 `ports`。
→ 检查题（`REDIS_URL` 写什么、redis 要不要 ports）答对：「写 redis:6379/0，不用，因为走的是容器端口」。

### 练习 2 实操：用户写了三行后放弃

用户自己起笔：

```yaml
build ./app      # ❌ 缺冒号
ports            # ❌ 裸键，没有值
```

连续两处 YAML 语法错误后说「我不会写，你写完。我学习下」→ 按规则直接给完整实现并逐段讲解（§8、§9、§10）。
用户需要补的不是 Docker 概念，而是 **compose 的 YAML 结构**（服务块字段名、列表写法、健康检查语法）。

### 检查题：把 `@postgres` 改回 `@localhost` 会怎样

答：「失败呀」✅
补充现场：`{"app":"ok","db":"down","redis":"up","db_error":"... Connection refused"}` —— 只有 db 挂，说明 `/health` 要分项报告的价值。

---

## 四、踩坑速查表

| 错误写法 / 现象 | 原因 | 正确写法 |
|---|---|---|
| 改了容器里的文件，重启「怎么又变回去了」 | 写进了可写层，删容器即销毁 | 改 Dockerfile / 挂 volume |
| 容器里 `pip install` 修好了，重建就没了 | 同上 | 依赖写进 `RUN pip install` |
| `COPY . .` 放在 `RUN pip install` 前面 | 每次改代码都重装依赖 | 先 `COPY requirements.txt .` |
| `-p 8080:80` 后访问 `localhost:80` 打不开 | 容器 80 没映射到宿主 80 | 访问 `localhost:8080` |
| 容器起来了但 `curl` 不通 | uvicorn 绑了 `127.0.0.1` | `--host 0.0.0.0` |
| `CMD uvicorn app:app` 结果进程行为怪 | shell 形式，信号不透传 | `CMD ["uvicorn", "app:app", ...]` |
| 宿主机 `psql -h localhost` 连不上 compose 的 pg | 没写 `ports`，只在 compose 内网可见 | 加 `ports: ["5432:5432"]`（仅调试用） |
| app 容器里 `@localhost:5432` 连不上 | `localhost` = app 容器自己 | `@postgres:5432`（服务名） |
| `compose up` 后 app 报 `Connection refused` 后自己好了 | PG 启动 ≠ 就绪 | `depends_on: condition: service_healthy` + healthcheck |
| `docker compose down` 后数据没了 | 没挂命名卷 | `volumes: [pgdata:/var/lib/postgresql/data]` |
| 写 `build ./app` 构建报错 | YAML 缺冒号空格 | `build: ./app` |
| `ports` 裸写一行 | YAML 键无值 | `ports:` + 列表项 |
| Docker Hub 拉取 `i/o timeout` | DNS 污染，直连 `auth.docker.io` 不通 | 重试 / 挂代理 |

---

## 五、环境备忘

- Docker Desktop 装好（29.4.3 / compose v5.1.3），但**守护进程需手动启动**：`open -a Docker`，等鲸鱼图标变绿
- Docker Hub 直连被 DNS 污染（`auth.docker.io` 解析到 `185.45.7.97` 等不可达 IP），拉镜像偶发 `DeadlineExceeded`；重试通常能过，必要时给 Docker Desktop 配代理 `http://127.0.0.1:7897`
- PyPI 直连正常（`pypi.org` 200），容器内 `pip install` 不需要镜像源
- 清理：`docker compose down -v`、`docker rm -f <容器>`、`docker image prune -a`
- 本项目 Docker 相关文件尚未接入 `4工程化/阶段项目-工程化TodoAPI`（留给第五阶段项目「Todo 实时协作版」做完整 Docker 化）

---

## 六、下一步

- 第五阶段下一项：**22 Celery + Redis** — 异步任务队列、定时任务
- 阶段项目：Todo 实时协作版（WebSocket + Celery 到期提醒 + Docker 化）
