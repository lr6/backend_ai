# 0.4 虚拟环境 & 包管理 — 学习笔记

## 前端类比

| 概念 | JavaScript | Python |
|------|------------|--------|
| 项目依赖目录 | `node_modules/` | `.venv/`（虚拟环境） |
| 包管理器 | npm / yarn / pnpm | pip |
| 安装命令 | `npm install axios` | `pip install requests` |
| 项目配置文件 | `package.json` | `pyproject.toml` |
| 依赖锁定 | `package-lock.json` | `requirements.txt` |
| 从配置安装 | `npm install` | `pip install -r requirements.txt` |

**关键区别**：npm 默认项目级安装（node_modules），pip 默认全局安装，需要手动创建 venv 实现项目隔离。

## 核心命令速查

```bash
# 虚拟环境
python -m venv .venv          # 创建
source .venv/Scripts/activate # 激活 (Git Bash / Linux)
.venv\Scripts\activate        # 激活 (CMD)
deactivate                    # 退出

# 直接用 venv 的 Python（跳过激活）
.venv/Scripts/python.exe your_script.py

# pip 日常
pip install requests           # 安装
pip install requests==2.28.0   # 安装指定版本
pip uninstall requests         # 卸载
pip list                       # 查看已安装
pip show requests              # 查看某包详情
pip freeze > requirements.txt  # 导出依赖
pip install -r requirements.txt # 从文件安装所有依赖
```

## pyproject.toml 结构

```toml
[project]
name = "todo-cli"
version = "0.1.0"
description = "命令行 Todo 工具"
requires-python = ">=3.10"
dependencies = [
    "requests>=2.28",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "mypy>=1.0",
]
```

| pyproject.toml | package.json |
|----------------|-------------|
| `[project]` name/version | `"name"`, `"version"` |
| `dependencies` | `"dependencies"` |
| `[project.optional-dependencies] dev` | `"devDependencies"` |
| `requires-python` | `"engines": { "node" }` |

## 标准项目结构

```
project/
├── .venv/              # 虚拟环境（gitignore）
├── pyproject.toml      # 项目配置
├── requirements.txt    # pip freeze 生成
├── .gitignore          # 忽略 .venv/
└── main.py
```

## 关键认知

- **sys.prefix != sys.base_prefix** → 在虚拟环境中
- **try/except ImportError** → 检测包是否安装
- **__import__('包名')** → 动态导入，等价于 `import 包名`
- **requirements.txt 格式**：`包名==版本` 或 `包名`，`#` 开头为注释

## 踩坑记录

- **Git Bash 下 `source activate` 可能不生效**：直接调用 `.venv/Scripts/python.exe` 即可绕过，效果一样
- **`None` vs `'None'`**：`'None'` 是字符串，不是 Python 的 None，别加引号
- **`and` vs `or`**：跳过条件用 `or`（空行或注释），不是 `and`（不可能同时满足）
- **`.venv/` 不要提交到 git**：在 `.gitignore` 中添加 `.venv/`
- **Windows 下 Python 路径注意**：路径中的 `\S` 在字符串中会被当成转义符，文档字符串里写路径会导致 SyntaxWarning
