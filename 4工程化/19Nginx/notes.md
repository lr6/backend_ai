# 19 Nginx — 反向代理、负载均衡、静态文件

> 日期：2026-11-15　｜　练习：`nginx.conf`（5 个练习，12 条断言全绿）　｜　测试：`check.py`

---

## 一、知识点讲解

### 1. uvicorn 是什么（用户主动提问引出的基础）

对照 Vue 世界：

| Vue 世界 | FastAPI 世界 |
|---------|-------------|
| `.vue` 组件 | `main.py` 里的 `app` |
| Vite dev server（`npm run dev`） | **uvicorn** |
| 浏览器访问 `5173` | 客户端访问 `8000` |

**uvicorn 是一个 Python Web 服务器进程**，负责：

1. 监听 TCP 端口（占住 8000）
2. 把 HTTP 报文翻译成 Python 调用（路径、方法、头、body）
3. 把返回值翻译回 HTTP 响应写回 socket

FastAPI 自己**不碰端口**，它只是一个符合 ASGI 协议的可调用对象：

```python
async def app(scope, receive, send):  # scope=请求信息, receive=读 body, send=写响应
    ...
```

**ASGI = FastAPI 和 uvicorn 之间的插座标准**（Flask 时代是同步的 WSGI）。

```
HTTP 请求 → uvicorn（服务器）→ ASGI 协议 → FastAPI（框架）→ 你的代码
```

`uvicorn main:app --reload`：`main:app` 是「插哪个 app」，uvicorn 是「谁在监听」。

> 关键：`uvicorn main:app` 起的是**一个**进程，服务器循环和 app 对象住在同一个进程里。uvicorn 退出，app 跟着消失。

### 2. 正向代理 vs 反向代理

```
正向代理（替客户端出头）              反向代理（替服务器出头）
 你 → [代理] → 任意网站               你 → 某个域名 → [Nginx] → 背后一堆 uvicorn
           ↑                                ↑
     客户端知道自己在用代理              客户端以为 Nginx 就是服务器
```

- **判断标准**：代理替谁出头。替客户端 = 正向；替服务器 = 反向。
- **一句话**：正向代理对方不知道你是谁，反向代理你不知道对方是谁。
- 正向代理例子：Clash、公司出口代理。
- 反向代理例子：Nginx、`api.example.com` 后面藏几台机器。
- Vite 的 `server.proxy` 也是反向代理，只是跑在 Node 里、只用于开发。
- 顺带解释了一个老问题：本地开发没被 CORS 卡过，因为浏览器眼里始终只有 `5173` 一个源（同源绕过浏览器拦截，代价是 Node 当替身）。

### 3. 为什么 uvicorn 前面要有 Nginx

| 活 | 为什么交给 Nginx |
|----|----------------|
| HTTPS 证书 | Nginx 终止 TLS，证书只配一处；换证书不重启应用 |
| 静态文件 | C 写的专用文件服务器，比 Python 发 `dist/` 快一个数量级 |
| 负载均衡 | 一个 uvicorn 进程 = 单核 Python；多开进程由 Nginx 分发 |
| 慢连接/大请求缓冲 | 先收完整请求再转给 uvicorn，防止慢客户端占死 Python 进程 |
| 网关杂活 | gzip、限流、访问日志、`client_max_body_size`、IP 封禁、健康检查 |

**Nginx 管「连接和流量」，uvicorn 管「业务逻辑」。**

### 4. Nginx 配置的五层结构

```nginx
# ① main（全局）—— 进程级参数
worker_processes 1;

# ② events —— 单进程能处理多少连接
events { worker_connections 1024; }

# ③ http —— 所有 HTTP 相关的总闸
http {
    # ④ server —— 一个站点（listen + server_name 唯一定位）
    server {
        listen 8080;
        server_name localhost;

        # ⑤ location —— 路由规则
        location /api/ {
            proxy_pass http://127.0.0.1:8000/;
        }
    }
}
```

| Nginx | Vue 世界 |
|-------|---------|
| `http {}` | 整个 router 配置文件 |
| `server {}` | 一个 router 实例 |
| `location {}` | `routes` 里的一条路由 |
| `proxy_pass` / `root` | 路由对应的 `component` |

**层级是硬约束**：`listen` 只能写进 `server`，`server` 只能进 `http`，`location` 只能进 `server`。

**分号规则**：分号是「简单指令」的结束符；块指令（`http` / `server` / `location` / `upstream`）的 `}` 后面什么都不加。

### 5. proxy_pass 末尾斜杠

| 配置 | 访问 `/api/todos` → 后端收到 |
|------|---------------------------|
| `proxy_pass http://127.0.0.1:8000/;`（带 `/`） | `/todos`（`/api/` 被替换成 `/`） |
| `proxy_pass http://127.0.0.1:8000;`（不带 `/`） | `/api/todos`（原样转发） |

两种都常见，但必须和 FastAPI 路由保持一致，否则满屏 404。

### 6. 静态文件 + SPA 回退

```nginx
location / {
    root /path/to/static;
    try_files $uri $uri/ /index.html;
}
```

- 文件路径 = `root` + 请求 URI
- `try_files`：按顺序试，**找到就停，最后一个当兜底**（内部跳转，重新走 location 匹配）
- 这就是 **Vue Router history 模式**「随便刷新不 404」的生产环境配置

### 7. 请求头透传（proxy_set_header）

请求走代理后，后端看到的连接全部来自 nginx（127.0.0.1）——在 uvicorn 眼里全世界只有一个客户端。后果：日志全是 127.0.0.1、按 IP 限流失效、绝对链接指向 `127.0.0.1:8000`。

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

| 头 | 变量 | 作用 |
|----|------|------|
| `Host` | `$host` | 用户访问的域名（默认会被换成 `$proxy_host` = `127.0.0.1:8000`） |
| `X-Real-IP` | `$remote_addr` | 真实客户端 IP（单个值） |
| `X-Forwarded-For` | `$proxy_add_x_forwarded_for` | IP 链，**追加**不覆盖 |

- 为什么 XFF 不用 `$remote_addr`：前面可能还有 CDN/负载均衡，`$proxy_add_x_forwarded_for` 保留已有链再追加，形成 `用户IP, CDN的IP, nginx的IP`。用 `$remote_addr` 会覆盖掉前一段。
- uvicorn 默认开启 `--proxy-headers`，且只信任来自 `127.0.0.1` 的 XFF，会把 `request.client` 改写成 XFF 里的值。
- **安全**：XFF 可由客户端伪造，只该信任来自已知代理的那一段；公网直连 uvicorn 时这条信任反而是漏洞。

### 8. 负载均衡（upstream）

一个 uvicorn 进程只能用单核（GIL），想扛量就多开进程，由 Nginx 分发：

```nginx
upstream todo_cluster {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
}

location /api/ {
    proxy_pass http://todo_cluster/;
}
```

- `upstream` 必须写在 `http` 块里（和 `server` 平级），不能写进 `location`
- `proxy_pass` 里的名字必须完全一致，末尾斜杠别丢（丢了前缀不剥）
- 默认轮询（round-robin）；其他：`least_conn`、`ip_hash`（同一 IP 固定一台）、`weight`
- 健康检查：开源版只有**被动**的 `max_fails` / `fail_timeout`；主动探活是 Nginx Plus

### 9. location 匹配优先级

```
1. location = /path        精确匹配 —— 最高优先级，命中即结束
2. 前缀匹配（普通 / ^~）    比较所有前缀，选「最长」的
3. 最长前缀带 ^~           → 直接用，不再看正则
4. 否则按书写顺序试正则 ~ / ~*  → 第一条命中的赢
5. 正则全不中              → 用第 2 步的最长前缀
```

- 前缀是**最长优先**，不是先写先赢；正则是**先写先赢**
- `^~` 不是匹配规则，是「命中后跳过正则」的开关
- 例：`/img/logo.png` 同时匹配 `^~ /img/` 和 `~* \.png$`，`^~` 让它止步于前缀

---

## 二、练习 ↔ 知识点映射

| 练习 | 内容 | 对应知识点 |
|------|------|-----------|
| 1 | 静态文件 + SPA 回退 | 第 6 节 `root`、`try_files` |
| 2 | `/api/` → 8000 且剥前缀 | 第 5 节 proxy_pass 斜杠 |
| 3 | 三条 `proxy_set_header` | 第 7 节 请求头透传 |
| 4 | `upstream` + 轮询 | 第 8 节 负载均衡 |
| 5 | `=` / `^~` / `~*` / 前缀 | 第 9 节 匹配优先级 |

---

## 三、练习纠错全记录

### 探底 1：Vite 的 proxy 是谁在转发？

- 回答：「以 /api 开头的请求转发到 localhost:8000，本地启动了一个服务器处理」
- 基本正确。补充：转发的是 **Vite dev server（Node 进程）**，不是浏览器；浏览器始终只跟 5173 打交道，所以本地开发没被 CORS 卡过。

### 探底 2：为什么不直接暴露 uvicorn？

- 用户跳过这题，转而问「uvicorn 是什么」——说明「服务器」和「框架」的边界没建立，先补了 uvicorn / ASGI 基础。

### 检查题：uvicorn 崩了，app 还在内存里吗？

- 回答：「main:app 是指 FastAPI 的 app，uvicorn 不知道谁在监听」
- 前半句对，后半句把角色说反了：**监听者就是 uvicorn**；app 连 socket 都不认识，只是被 import 进同一进程的对象，进程退了两者一起消失。
- 纠正后引出「Nginx 管连接、uvicorn 管业务」的分工。

### 检查题：怎么判断正向还是反向代理？

- 回答：「看他是代理客户端，还是服务器端」——✅ 正确。

### 练习 4：`serve` + 多余分号

现象：

```
nginx: [emerg] unknown directive "serve" in .../nginx.conf:39
```

原因：`server` 拼成了 `serve`；改完又出现

```
nginx: [emerg] unexpected ";" in .../nginx.conf:41
```

原因：`upstream {...};` 块结尾多了分号。**分号只属于简单指令，块指令 `}` 后面什么都不加。**

### 练习 5：return 语法两连错

1. `return "caret_tilde"` —— 裸字符串不合法。`return` 合法形式：
   - `return 200;`
   - `return 200 "文本";`
   - `return 301 https://...;`
2. `return 200 "..."` 缺分号，报错却指向下一行的 `}`：

```
nginx: [emerg] unexpected "}" in .../nginx.conf:112
```

**经验：Nginx 报 `}` 的错，往往问题在上一行（读到 `}` 才发现上一句没结束）。**

### 练习 5：`location /img` 输给正则

现象：`/img/logo.png` 返回了正则那条的结果。

原因：前缀不带 `^~` 时，Nginx 在最长前缀命中后仍会检查正则，`~* \.png$` 更早赢。加上 `^~` 才能「命中前缀后不再看正则」。

另外把 `/img` 改成 `/img/`：`/img` 会连带匹配 `/imgfoo`。

### 练习 5：响应体写成了正则表达式

`return 200 "~* \.(png|jpg)$"` —— 约定要返回结果文本 `regex`，不是规则本身。

---

## 四、踩坑速查表

| 错误写法 | 报错 / 现象 | 正确写法 |
|---------|-----------|---------|
| `serve 127.0.0.1:8000;` | `unknown directive "serve"` | `server 127.0.0.1:8000;` |
| `upstream x { ... };` | `unexpected ";"` | `upstream x { ... }` |
| `return "文本"` | `invalid return code` | `return 200 "文本";` |
| `return 200 "文本"` 缺分号 | 报错指向下一行 `}` | 补 `;` |
| `location /img` + 正则同存 | 正则抢先，返回错误分支 | `location ^~ /img/` |
| `proxy_pass http://x:8000;` | 后端收到 `/api/...`，404 | `proxy_pass http://x:8000/;` |
| `proxy_pass http://todo_cluster` 丢斜杠 | 前缀不剥，404 | `proxy_pass http://todo_cluster/;` |
| upstream 写进 location | `"upstream" directive is not allowed here` | 移到 `http` 块 |
| 不改 `proxy_set_header` | 后端 `x_real_ip=None`、Host=`127.0.0.1:8000` | 三条 set_header |

---

## 五、常用命令

```bash
# 语法检查（改完先跑这个）
nginx -t -p "$PWD" -c "$PWD/nginx.conf"

# 用本目录配置启动 / 重载 / 停止
nginx -p "$PWD" -c "$PWD/nginx.conf"
nginx -p "$PWD" -c "$PWD/nginx.conf" -s reload
nginx -p "$PWD" -c "$PWD/nginx.conf" -s stop

# 看真实请求记录（练习里可以直接观察）
tail -f runtime/access.log
```

`reload` 是**平滑重载**：不中断现有连接，旧 worker 处理完手里的请求再退出——这是 Nginx 部署改配置不重启的常规做法。

---

## 六、生产延伸（本次未动手，留作对照）

- **正则抢代理**：`location /api/` 不带 `^~` 时，`~* \.(png|jpg)$` 会把 `/api/export.png` 从代理手里抢走。生产上给 API 前缀加 `^~`，或把正则写具体。
- **请求体大小**：默认 `client_max_body_size 1m`，上传大文件会收到 413，需要显式调大。
- **超时**：`proxy_read_timeout` 默认 60s，长任务要调；反之应用侧不该同步跑长任务。
- **TLS 终止**：证书配在 Nginx，uvicorn 只收明文；`X-Forwarded-Proto` 告诉后端原始协议。
- **gzip**：静态资源开启压缩；API 的 JSON 是否压缩看场景。
- **访问日志**：`$remote_addr $request $status $body_bytes_sent` 是排查问题的第一手资料。
- **多 worker**：`worker_processes auto` + `worker_connections`，Nginx 自身也能多进程分摊连接。
