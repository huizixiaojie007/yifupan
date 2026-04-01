from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.stock_collection import StockCollection
from repositories.stock_collection_repo import StockCollectionRepo
from schemas.stock_collection import StockCollectionCreate, ToggleCollectionRes, ToggleCollectionReq
from schemas.zhangting_info import ZhangtingInfoCreate
from models import ZhangtingInfo
from fastapi import HTTPException  # 模拟Web框架的异常（实际可替换为自定义异常）

class StockCollectionService:
    """业务逻辑类"""

    def __init__(self, db: Session):
        """初始化数据库会话和数据访问层实例"""
        self.db = db
        self.collect_repo = StockCollectionRepo(db)  # 依赖注入数据访问层

    def add_collect_info(req: ToggleCollectionReq) -> ToggleCollectionRes:
        """添加收藏信息"""
        # success, msg = StockCollectionRepo.upsert_collection(req)
        # return ToggleCollectionRes(
        #     success=success,
        #     message=msg,
        #     data={"gpName": req.gpNo, "isCollect": req.isCollect}
        # )
        result = StockCollectionRepo.create(collect_in = req)
        return result


    def get_collect_info(self, name, date, data) -> bool:
        """更新涨停信息（包含业务逻辑）"""
        update = self.collect_repo.update_by_user_date(date, name, data)
        self.db.commit()
        return update

# stock_collection_service = StockCollectionService()
