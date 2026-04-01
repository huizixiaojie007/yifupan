from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from config import SessionLocal
from services.user_service import UserService
from schemas.user import UserCreate, UserSchema, Token
from utils.jwt_utils import create_access_token, verify_token, ACCESS_TOKEN_EXPIRE_MINUTES

# 依赖：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# OAuth2 密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# 创建路由
router = APIRouter(prefix="/api/auth", tags=["认证"])


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> UserSchema:
    """获取当前登录用户"""
    payload = verify_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_service = UserService(db)
    user = user_service.get_user_by_username(username)
    return UserSchema.model_validate(user)


@router.post("/register", response_model=UserSchema, summary="用户注册")
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """
    用户注册接口
    
    - **username**: 用户名（3-50个字符）
    - **password**: 密码（至少6个字符）
    - **email**: 邮箱（可选）
    """
    try:
        print(f"[注册接口] 收到注册请求: username={user_in.username}, email={user_in.email}")
        
        # 验证输入（Pydantic已经做了基础验证，这里做额外检查）
        if not user_in.username or len(user_in.username.strip()) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名长度至少3个字符"
            )
        
        if not user_in.password or len(user_in.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="密码长度至少6个字符"
            )
        
        # 创建用户
        user_service = UserService(db)
        user = user_service.register_user(user_in)
        
        # 直接使用对象，repository 已经确保对象状态正确
        print(f"[注册接口] 用户注册成功: id={user.id}, username={user.username}")
        return UserSchema.model_validate(user)
        
    except HTTPException:
        # 重新抛出HTTP异常（业务逻辑异常）
        raise
    except Exception as e:
        # 记录详细错误信息
        print(f"[注册接口] 注册过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败，请稍后重试"
        )


@router.post("/login", response_model=Token, summary="用户登录")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    用户登录接口
    
    使用 OAuth2 密码流格式：
    - **username**: 用户名
    - **password**: 密码
    
    返回 JWT token 和用户信息
    """
    user_service = UserService(db)
    user = user_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserSchema.model_validate(user)
    }


@router.get("/me", response_model=UserSchema, summary="获取当前用户信息")
def get_current_user_info(
    current_user: UserSchema = Depends(get_current_user)
):
    """
    获取当前登录用户的信息
    
    需要提供有效的 JWT token
    """
    return current_user

