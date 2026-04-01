
from sqlalchemy import Column, Integer, String, Boolean, Float, BigInteger, Time, Date, DateTime, Index
# from datetime import datetime, time,date

from config import Base  # 继承基础模型类


class StockCollection(Base):
    __tablename__ = "stock_collection"  # 数据库表名
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
    gp_name = Column(String(100))  # 股票名称
    user = Column(String(50))  # 用户名
    date = Column(Date, nullable=True)#日期
    collect = Column(Boolean, nullable=False) #收藏

    create_time = Column(DateTime)  # 创建时间
    update_time = Column(DateTime)  # 更新时间

    def __repr__(self):
        """打印模型时的格式"""
        return f"<StockCollection(id={self.id}, gp_name='{self.gp_name}', gp_name='{self.date})>"
