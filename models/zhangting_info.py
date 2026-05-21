
from sqlalchemy import Column, Integer, String, Boolean, Float, BigInteger, Time, Date, DateTime, Index
# from datetime import datetime, time,date

from config import Base  # 继承基础模型类


class ZhangtingInfo(Base):
    __tablename__ = "zhangting_info"  # 数据库表名
    # 关键：必须放在 __tablename__ 下方，作为类属性
    __table_args__ = {
        'extend_existing': True,  # 允许表已存在时扩展定义
        'sqlite_autoincrement': True  # 可选：SQLite自增ID兼容（如果用SQLite）
    }
    # 添加索引
    __table_args__ = (
        Index("date", "date"),  # 索引名+字段名
    )
    id = Column(Integer, primary_key=True, index=True)
    gp_no = Column(String(50), index=True)  # 股票代码
    gp_name = Column(String(100))  # 股票名称
    curr_price = Column(String(50))  # 现价
    limitup_range = Column(String(50))  # 涨跌幅
    first_limitup_time = Column(Time, nullable=True)  # 首次涨停时间
    last_limitup_time = Column(Time, nullable=True)  # 最终涨停时间
    limitup_days = Column(String(50))  # 连续涨停天数
    limitup_reason = Column(String(200))  # 涨停原因
    limitup_reason_detail = Column(String(1000))  # 涨停原因
    limitup_order_volume = Column(String(50))  # 封单量
    limitup_order_amount = Column(String(50))  # 封单额
    limitup_seal_ratio = Column(String(50))  # 封成比
    limitup_flow_ratio = Column(String(50))  # 封流比
    limitup_open_times = Column(String(50))  # 开板次数
    value = Column(String(50))  # 流通市值
    day_limitup = Column(String(50))  # 几天几板
    sector = Column(String(200))  # 板块
    sector_reason = Column(String(200))  # 板块原因
    turnover_rate = Column(String(50))  # 换手率
    limitup_type = Column(String(100))  # 版型
    score = Column(String(100))  # 版型
    date = Column(Date, nullable=True)#日期
    longhu = Column(Boolean, nullable=False) #龙虎榜
    longhu_detail = Column(String(2000))  # 龙虎榜详情

    create_time = Column(DateTime)  # 创建时间
    update_time = Column(DateTime)  # 更新时间

    def __repr__(self):
        """打印模型时的格式"""
        return f"<ZhangtingInfo(id={self.id}, gp_no='{self.gp_no}', gp_name='{self.gp_name}')>"
