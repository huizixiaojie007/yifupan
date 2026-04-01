from typing import Optional
from sqlalchemy.orm import Session
from models.user import User
from schemas.user import UserCreate
from utils.password_utils import get_password_hash


class UserRepo:
    """用户数据访问层"""
    
    def __init__(self, db: Session):
        """初始化数据库会话"""
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """根据ID查询用户"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_username(self, username: str) -> Optional[User]:
        """根据用户名查询用户"""
        return self.db.query(User).filter(User.username == username).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """根据邮箱查询用户"""
        return self.db.query(User).filter(User.email == email).first()
    
    def create(self, user_in: UserCreate) -> User:
        """创建新用户"""
        try:
            # 加密密码
            hashed_password = get_password_hash(user_in.password)
            
            # 创建用户对象（手动设置时间戳，避免依赖数据库默认值）
            from datetime import datetime
            now = datetime.now()
            db_user = User(
                username=user_in.username,
                email=user_in.email,
                hashed_password=hashed_password,
                create_time=now,
                update_time=now
            )
            
            # 写入数据库
            self.db.add(db_user)
            # self.db.flush()  # 刷新到数据库，获取自增ID和默认值
            
            # # 在 flush 后立即获取所有需要的信息（此时对象还在会话中，可以安全访问）
            # user_id = db_user.id
            # username = db_user.username
            # email = db_user.email
            # hashed_pwd = db_user.hashed_password
            # is_active = db_user.is_active
            # is_superuser = db_user.is_superuser
            # create_time = db_user.create_time
            # update_time = db_user.update_time
            
            # 提交事务
            self.db.commit()
            self.db.refresh(db_user)

            # # commit 后，创建一个新的对象（不在会话中），避免对象分离问题
            # # 这样可以确保返回的对象是有效的，不会因为会话问题而无法访问
            # result_user = User(
            #     id=user_id,
            #     username=username,
            #     email=email,
            #     hashed_password=hashed_pwd,
            #     is_active=is_active,
            #     is_superuser=is_superuser,
            #     create_time=create_time,
            #     update_time=update_time
            # )
            #
            # # 将对象添加到会话中，以便后续操作可以使用
            # self.db.merge(result_user)
            
            return db_user
        except Exception as e:
            self.db.rollback()  # 发生错误时回滚
            raise
    
    def update(self, user_id: int, update_data: dict) -> Optional[User]:
        """更新用户信息"""
        try:
            user = self.get_by_id(user_id)
            if not user:
                return None
            
            for key, value in update_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            # 更新更新时间
            from datetime import datetime
            user.update_time = datetime.now()
            
            self.db.commit()
            # commit 后对象已经有了更新后的信息，不需要 refresh
            return user
        except Exception as e:
            self.db.rollback()
            raise

