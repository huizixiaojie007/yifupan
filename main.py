# -*- coding: utf-8 -*-
# main.py（修正导入）

from fastapi import FastAPI  # 只从fastapi导入FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse  # 从starlette.responses导入RedirectResponse
from fastapi.staticfiles import StaticFiles
from config import Base, engine

# 先尝试导入认证路由（重要功能，优先导入）
try:
    from api.auth_api import router as auth_router
    auth_router_available = True
    print("✓ 认证路由模块导入成功")
except Exception as e:
    print("✗ 警告: 无法导入认证路由: {0}".format(e))
    import traceback
    traceback.print_exc()
    print("请运行: pip install python-jose[cryptography] passlib[bcrypt] python-multipart email-validator")
    auth_router_available = False
    auth_router = None

# 再导入其他业务路由
try:
    import sys
    import os
    # 添加项目根目录到Python路径
    sys.path.append(os.getcwd())
    print("开始导入涨停路由模块...")
    from api.zhangting_api import router as zhangting_router
    zhangting_router_available = True
    print("✓ 涨停路由模块导入成功")
except Exception as e:
    print("✗ 警告: 无法导入涨停路由: {0}".format(e))
    import traceback
    traceback.print_exc()
    zhangting_router_available = False
    zhangting_router = None

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="股票涨停系统 API",
    description="包含用户认证和股票数据查询功能",
    version="1.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 根路径重定向到前端页面
@app.get("/")
def root():
    return RedirectResponse(url="/public/index.html")

# 登录页面路由
@app.get("/login")
def login_page():
    return RedirectResponse(url="/public/login.html")

# 注册路由（必须在静态文件之前注册，确保API路由优先匹配）
if auth_router_available:
    app.include_router(auth_router)  # 先注册认证路由
    print("✓ 认证路由已注册到应用")
else:
    print("✗ 认证路由未注册（缺少依赖）")

if zhangting_router_available:
    app.include_router(zhangting_router)  # 再注册其他业务路由
    print("✓ 涨停路由已注册到应用")

# 挂载静态资源（放在最后，避免拦截API路由）
app.mount("/public", StaticFiles(directory="public"), name="public")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=False)