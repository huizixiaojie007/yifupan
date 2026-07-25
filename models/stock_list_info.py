from sqlalchemy import Column, Integer, String, DateTime, Index

from config import Base


class StockListInfo(Base):
    __tablename__ = "stock_list_info"
    
    __table_args__ = (
        Index("idx_gp_code", "gp_code"),
        Index("idx_gp_name", "gp_name"),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    gp_code = Column(String(10), index=True, comment='股票代码')
    gp_name = Column(String(11), comment='股票名称')
    curr_price = Column(String(11), comment='现价')
    change_percent = Column(String(11), comment='涨跌幅')
    change_amount = Column(String(11), comment='涨跌额')
    amplitude = Column(String(11), comment='振幅')
    volume_ratio = Column(String(11), comment='量比')
    low = Column(String(11), comment='最低价')
    high = Column(String(11), comment='最高价')
    open = Column(String(13), comment='今开')
    prev_close = Column(String(11), comment='昨收')
    volume = Column(String(20), comment='成交量')
    amount = Column(String(20), comment='成交额')
    turnover_rate = Column(String(11), comment='换手率')
    pe_ttm = Column(String(11), comment='市盈率')
    pb = Column(String(11), comment='市净率')
    total_market_cap = Column(String(20), comment='总市值')
    float_market_cap = Column(String(20), comment='流通市值')
    create_time = Column(DateTime)
    update_time = Column(DateTime)

    def __repr__(self):
        return f"<StockListInfo(id={self.id}, gp_code='{self.gp_code}', gp_name='{self.gp_name}')>"
