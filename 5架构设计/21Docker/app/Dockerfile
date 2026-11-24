# =====================================================
# 练习 1：给这个 FastAPI 应用写 Dockerfile
#
# 目标：docker build 成功 → docker run 起来后能访问 /greeting
# 完成后在 21Docker/ 目录跑：python check.py
#
# 你需要写 6 行（每条指令一行，顺序见讲解）：
#
#   1. FROM    基础镜像用 python:3.12-slim
#   2. WORKDIR 容器内的工作目录，用 /app
#   3. COPY    只拷 requirements.txt 到当前工作目录
#   4. RUN     pip install -r requirements.txt
#              （国内网络慢可以加 -i https://pypi.tuna.tsinghua.edu.cn/simple）
#   5. COPY    把其余代码拷进去（源写 . ，目标写当前目录）
#   6. CMD     启动 uvicorn：main 模块是 app，对象也叫 app，
#              --host 0.0.0.0，--port 8000
#              注意用 JSON 数组形式写
#
# 提示：不要把 5 挪到 4 前面，那是刚才讲的缓存问题
# =====================================================


FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]