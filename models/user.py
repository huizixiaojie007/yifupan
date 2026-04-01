from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from config import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"  # 数据库表名
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)  # 用户名（唯一）
    email = Column(String(100), unique=True, index=True, nullable=True)  # 邮箱（唯一，可选）
    hashed_password = Column(String(255), nullable=False)  # 加密后的密码
    is_active = Column(Boolean, default=True)  # 是否激活
    is_superuser = Column(Boolean, default=False)  # 是否超级用户
    create_time = Column(DateTime, default=datetime.now)  # 创建时间
    update_time = Column(DateTime, default=datetime.now, onupdate=datetime.now)  # 更新时间
    
    def __repr__(self):
        """打印模型时的格式"""
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

