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

# 服务端登录检查中间件
from starlette.middleware.base import BaseHTTPMiddleware
from jose import jwt
from utils.jwt_utils import SECRET_KEY, ALGORITHM
from sqlalchemy.orm import Session
from models.user import User
from config import SessionLocal

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # 允许访问的路径（静态文件和登录相关页面）
        allowed_paths = [
            "/public/login.html",
            "/public/index.html",
            "/public/css/",
            "/public/js/",
            "/public/img/",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/send-verification-code",
            "/api/auth/reset-password",
            "/docs",
            "/openapi.json"
        ]
        
        # 获取请求路径
        path = request.url.path
        
        # 检查是否是允许的路径
        is_allowed = False
        for allowed_path in allowed_paths:
            if path == allowed_path or path.startswith(allowed_path):
                is_allowed = True
                break
        
        # 如果不是允许的路径，检查登录状态
        if not is_allowed:
            # 检查session中的登录状态（如果使用session）
            session_token = request.cookies.get("access_token")
            
            # 如果没有登录且尝试访问受保护页面，重定向到登录页
            if not session_token:
                return RedirectResponse(url="/public/login.html")
            
            # 检查管理页面权限
            if path.startswith("/public/admin.html") or path.startswith("/api/zhangting/stock/admin"):
                # 验证token并检查用户权限
                try:
                    payload = jwt.decode(session_token, SECRET_KEY, algorithms=[ALGORITHM])
                    username = payload.get("sub")
                    if not username:
                        return RedirectResponse(url="/public/login.html")
                    
                    # 查询用户是否是超级管理员
                    db: Session = SessionLocal()
                    user = db.query(User).filter(User.username == username).first()
                    db.close()
                    
                    if not user or not user.is_superuser:
                        # 非管理员用户，返回403或重定向到首页
                        return RedirectResponse(url="/public/index.html")
                except Exception as e:
                    print(f"验证管理页面权限失败: {e}")
                    return RedirectResponse(url="/public/login.html")
        
        response = await call_next(request)
        return response

# 挂载静态资源（放在中间件之前，避免被拦截）
import os
current_dir = os.path.dirname(os.path.abspath(__file__))
public_dir = os.path.join(current_dir, "public")
print(f"静态文件目录: {public_dir}")
print(f"静态文件目录是否存在: {os.path.exists(public_dir)}")
app.mount("/public", StaticFiles(directory=public_dir), name="public")

# 添加认证中间件（在静态资源之后，只保护API路由）
app.add_middleware(AuthMiddleware)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=3000, reload=False)