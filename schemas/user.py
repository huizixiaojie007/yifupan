from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
import re


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: Optional[str] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        """验证邮箱格式（如果提供了邮箱）"""
        if v is None or v == "":
            return None
        # 简单的邮箱格式验证
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError('邮箱格式不正确')
        return v


class UserCreate(UserBase):
    """创建用户模型"""
    password: str = Field(..., min_length=6, max_length=72, description="密码（最多72个字符）")


class UserLogin(BaseModel):
    """用户登录模型"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserSchema(UserBase):
    """用户响应模型"""
    id: int
    is_active: Optional[bool] = False
    is_superuser: Optional[bool] = False

    vip_date: Optional[datetime] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Token 响应模型"""
    access_token: str
    token_type: str = "bearer"
    user: UserSchema


class TokenData(BaseModel):
    """Token 数据模型"""
    username: Optional[str] = None

