"""
第一阶段 · 4 自动文档 — 检验练习

每个 TODO 需要你来实现。
写完后运行: .venv/bin/python practice.py
全部通过 = 自动文档 ✅

提示（前端对照）：
  - /docs (Swagger UI)  ~ 自动生成的 Postman，在线调试接口
  - /openapi.json       ~ 接口的 JSON 契约，前端可用它生成类型/调用代码
  - 文档自动从代码提取：路由 → paths，模型 → components/schemas
"""

from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.testclient import TestClient


# ===== 练习 1：自定义文档信息 =====
app = FastAPI(
    # TODO: 填入三个参数（key=value）：
    #   title="Todo API"
    #   description="一个待办事项管理接口"
    #   version="1.0.0"
    title='Todo API',
    description='一个待办事项管理接口',
    version='1.0.0'
)


# ===== 练习 2：定义一个模型，让它出现在 components/schemas =====
class Todo(BaseModel):
    """
    定义 Todo 模型，两个字段：
      - title: str
      - done: bool = False（默认 False）
    """
    # TODO
    title: str
    done: bool = False

@app.post('/todo')
def create_todo(todo: Todo):
    return todo


# ===== 练习 3：定义一个路由，让它出现在 paths =====
@app.get("/hello")
def hello():
    """
    返回 {"message": "world"}
    """
    # TODO
    return {'message': 'world'}


# ============================================
# 测试代码，不要修改下面内容
# ============================================
if __name__ == "__main__":
    client = TestClient(app)
    errors = []

    def check(name, actual, expected):
        if actual != expected:
            errors.append(f"{name}: 期望 {expected}，实际 {actual}")
        else:
            print(f"✅ {name}")

    # 拿 openapi.json 这个「契约」
    spec = client.get("/openapi.json").json()

    # 练习 1：自定义文档信息出现在 info 字段
    check("练习1 title", spec["info"]["title"], "Todo API")
    check("练习1 description", spec["info"]["description"], "一个待办事项管理接口")
    check("练习1 version", spec["info"]["version"], "1.0.0")

    # 练习 2：Pydantic 模型出现在 components/schemas
    schemas = spec.get("components", {}).get("schemas", {})
    check("练习2 有 Todo schema", "Todo" in schemas, True)
    todo_props = schemas.get("Todo", {}).get("properties", {})
    check("练习2 Todo 有 title 字段", "title" in todo_props, True)
    check("练习2 Todo 有 done 字段", "done" in todo_props, True)

    # 练习 3：路由出现在 paths
    check("练习3 有 /hello 路由", "/hello" in spec.get("paths", {}), True)
    check("练习3 /hello 支持 GET", "get" in spec.get("paths", {}).get("/hello", {}), True)

    # 练习 4：Swagger UI 页面可访问（不用写代码，验证文档页面存在）
    r = client.get("/docs")
    check("练习4 /docs 返回 200", r.status_code, 200)

    if errors:
        print(f"\n有 {len(errors)} 个测试没通过：")
        for e in errors:
            print("  " + e)
    else:
        print("\n🎉 全部通过！自动文档 = ✅")
