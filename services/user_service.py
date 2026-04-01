from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from repositories.user_repo import UserRepo
from schemas.user import UserCreate
from models.user import User
from utils.password_utils import verify_password


class UserService:
    """用户业务逻辑层"""
    
    def __init__(self, db: Session):
        """初始化数据库会话和数据访问层实例"""
        self.db = db
        self.user_repo = UserRepo(db)
    
    def register_user(self, user_in: UserCreate) -> User:
        """注册新用户"""
        # 检查用户名是否已存在
        if self.user_repo.get_by_username(user_in.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 检查邮箱是否已存在（如果提供了邮箱）
        if user_in.email and self.user_repo.get_by_email(user_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )
        
        # 创建用户
        return self.user_repo.create(user_in)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """验证用户登录"""
        user = self.user_repo.get_by_username(username)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="用户账户已被禁用"
            )
        
        return user
    
    def get_user_by_id(self, user_id: int) -> User:
        """根据ID获取用户"""
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        return user
    
    def get_user_by_username(self, username: str) -> User:
        """根据用户名获取用户"""
        user = self.user_repo.get_by_username(username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        return user

