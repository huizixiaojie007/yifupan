# schemas/stock_collection.py
from pydantic import BaseModel, Field
from datetime import datetime, time, date
from typing import Optional,Dict, Any

# 基础模型（共享字段）
class StockCollectionSchema(BaseModel):
    # 1. 添加缺失的 `id` 字段
    # id: int  # ID 是主键，通常是必需的
    gp_name: Optional[str] = None  # 股票名称
    user: Optional[str] = None  # 用户
    date: Optional[datetime] = None  # 日期
    collect: Optional[bool] = False  # 是否收藏

    # 日期时间字段：ORM模型是DateTime类型，Pydantic用Optional[datetime]接收
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    # 关键配置：允许从 SQLAlchemy ORM 模型转换为 Pydantic 模型
    class Config:
        from_attributes = True  # Pydantic v2 用这个；v1 用 orm_mode = True

# 创建数据时的模型（无需ID和时间，由数据库自动生成）
class StockCollectionCreate(StockCollectionSchema):
    pass


# -------------------------- 请求模型 --------------------------
class GetCollectionStatusReq(BaseModel):
    """查询收藏状态 - 请求参数（GET 方式用 Query 参数）"""
    user: str = Field(..., description="用户标识（用户名/用户ID）")
    gpNo: str = Field(..., description="股票代码")
    date: str = Field(..., description="收藏日期（格式：YYYY-MM-DD）")

class ToggleCollectionReq(BaseModel):
    """切换收藏状态 - 请求参数（POST 方式用 Body 参数）"""
    user: str = Field(..., description="用户标识")
    gpName: str = Field(..., description="股票名称")
    date: str = Field(..., description="收藏日期（YYYY-MM-DD）")
    isCollect: bool = Field(..., description="是否收藏（true=收藏，false=取消）")

# -------------------------- 响应模型 --------------------------
class BaseResponse(BaseModel):
    """基础响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="提示信息")

class GetCollectionStatusRes(BaseResponse):
    """查询收藏状态 - 响应结果"""
    collected: bool = Field(..., description="是否已收藏")

class ToggleCollectionRes(BaseResponse):
    """切换收藏状态 - 响应结果"""
    data: Optional[Dict[str, Any]] = Field(None, description="附加数据（可选）")