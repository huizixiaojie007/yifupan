from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from repositories.zhangting_info_repo import ZhangtingInfoRepo
from schemas.zhangting_info import ZhangtingInfoCreate
from models import ZhangtingInfo
from fastapi import HTTPException  # 模拟Web框架的异常（实际可替换为自定义异常）

class ZhangtingInfoService:
    """业务逻辑类"""

    def __init__(self, db: Session):
        """初始化数据库会话和数据访问层实例"""
        self.db = db
        self.zhangting_repo = ZhangtingInfoRepo(db)  # 依赖注入数据访问层

    def add_zhangting_info(self, zhangting_in: ZhangtingInfoCreate) -> ZhangtingInfo:
        """添加涨停信息（包含业务逻辑）"""

        db_zhangting = self.zhangting_repo.create(zhangting_in)
        db_zhangting.date = datetime.now().date()
        db_zhangting.create_time = datetime.now()
        db_zhangting.update_time = datetime.now()
        self.db.commit()
        self.db.refresh(db_zhangting)
        return db_zhangting

    def update_zhangting_info(self, name, date, data) -> bool:
        """更新涨停信息（包含业务逻辑）"""
        update = self.zhangting_repo.update_by_date(date, name, data)
        self.db.commit()
        return update



    def get_info(self, id: int) -> ZhangtingInfo:
        """获取用户信息（带权限校验）"""
        info = self.info_repo.get_by_id(id)
        if not info:
            raise HTTPException(status_code=404, detail="数据不存在")
        # 此处可添加权限校验（如仅管理员可查看其他用户）
        return info
