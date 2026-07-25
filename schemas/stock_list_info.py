from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class StockListInfoSchema(BaseModel):
    id: Optional[int] = None
    gp_code: Optional[str] = None
    gp_name: Optional[str] = None
    curr_price: Optional[str] = None
    change_percent: Optional[str] = None
    change_amount: Optional[str] = None
    amplitude: Optional[str] = None
    volume_ratio: Optional[str] = None
    low: Optional[str] = None
    high: Optional[str] = None
    open: Optional[str] = None
    prev_close: Optional[str] = None
    volume: Optional[str] = None
    amount: Optional[str] = None
    turnover_rate: Optional[str] = None
    pe_ttm: Optional[str] = None
    pb: Optional[str] = None
    total_market_cap: Optional[str] = None
    float_market_cap: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class StockListInfoCreate(StockListInfoSchema):
    pass


class StockListInfoUpdate(StockListInfoSchema):
    pass
