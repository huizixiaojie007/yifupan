# schemas/zhangting_info.py
from pydantic import BaseModel
from datetime import datetime, time, date
from typing import Optional

# 基础模型（共享字段）
class ZhangtingInfoSchema(BaseModel):
    # 1. 添加缺失的 `id` 字段
    # id: int  # ID 是主键，通常是必需的
    gp_no: Optional[str] = None  # 股票代码
    gp_name: Optional[str] = None  # 股票名称
    curr_price: Optional[str] = None  # 现价
    limitup_range: Optional[str] = None  # 涨跌幅
    first_limitup_time: Optional[time] = None  # 首次涨停时间（时间类型）
    last_limitup_time: Optional[time] = None  # 最终涨停时间（时间类型）
    limitup_days: Optional[str] = None  # 连续涨停天数
    limitup_reason: Optional[str] = None  # 涨停原因
    limitup_reason_detail: Optional[str] = None  # 涨停原因
    limitup_order_volume: Optional[str] = None  # 封单量
    limitup_order_amount: Optional[str] = None  # 封单额
    limitup_seal_ratio: Optional[str] = None  # 封成比
    limitup_flow_ratio: Optional[str] = None  # 封流比
    limitup_open_times: Optional[str] = None  # 开板次数
    value: Optional[str] = None  # 流通市值
    day_limitup: Optional[str] = None  # 几天几板
    sector: Optional[str] = None  # 板块
    sector_reason: Optional[str] = None  # 板块原因
    turnover_rate: Optional[str] = None  # 换手率
    limitup_type: Optional[str] = None  # 版型
    score: Optional[str] = None  # 综合得分
    date: Optional[datetime] = None  # 日期
    longhu: Optional[bool] = False  # 龙虎榜
    longhu_detail: Optional[str] = None  # 龙虎榜详情

    # 日期时间字段：ORM模型是DateTime类型，Pydantic用Optional[datetime]接收
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    # 关键配置：允许从 SQLAlchemy ORM 模型转换为 Pydantic 模型
    class Config:
        from_attributes = True  # Pydantic v2 用这个；v1 用 orm_mode = True

# 定义板块响应模型（字段名和后端返回的字典键一致）
class SectorResponse(BaseModel):
    # sector 允许为 None，默认值为空字符串
    sector: Optional[str] = ""
    # sector_reason 允许为 None，默认值为"暂无原因"
    sector_reason: Optional[str] = "暂无原因"
    # stock_count 允许为 None，默认值为 0（避免统计异常）
    latest_date_stock_count: Optional[int] = 0
    total_stock_count: Optional[int] = 0
    latest_date: Optional[datetime] = None

    # 可选：如果需要兼容 ORM 模型（如直接返回数据库模型对象），添加配置
    class Config:
        from_attributes = True  # 支持从 ORM 对象直接转换（SQLAlchemy 模型等）

# 创建数据时的模型（无需ID和时间，由数据库自动生成）
class ZhangtingInfoCreate(ZhangtingInfoSchema):
    pass