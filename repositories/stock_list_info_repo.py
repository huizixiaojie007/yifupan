from typing import List, Dict, Optional

from sqlalchemy import desc, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.stock_list_info import StockListInfo
from schemas.stock_list_info import StockListInfoCreate


class StockListInfoRepo:
    """股票列表信息数据访问类"""
    
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, id: int) -> Optional[StockListInfo]:
        """根据ID查询"""
        return self.db.query(StockListInfo).filter(StockListInfo.id == id).first()

    def get_by_code(self, gp_code: str) -> Optional[StockListInfo]:
        """根据股票代码查询"""
        return self.db.query(StockListInfo).filter(StockListInfo.gp_code == gp_code).first()

    def get_by_name(self, gp_name: str) -> Optional[StockListInfo]:
        """根据股票名称查询"""
        return self.db.query(StockListInfo).filter(StockListInfo.gp_name == gp_name).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> List[StockListInfo]:
        """获取所有股票列表"""
        return self.db.query(StockListInfo).offset(skip).limit(limit).all()

    def list_by_code_like(self, gp_code: str, skip: int = 0, limit: int = 100) -> List[StockListInfo]:
        """根据股票代码模糊查询"""
        return self.db.query(StockListInfo).filter(StockListInfo.gp_code.like(f"%{gp_code}%")).offset(skip).limit(limit).all()

    def list_by_name_like(self, gp_name: str, skip: int = 0, limit: int = 100) -> List[StockListInfo]:
        """根据股票名称模糊查询"""
        return self.db.query(StockListInfo).filter(StockListInfo.gp_name.like(f"%{gp_name}%")).offset(skip).limit(limit).all()

    def create(self, stock_in: StockListInfoCreate) -> StockListInfo:
        """添加新的股票列表信息"""
        db_stock = StockListInfo(
            gp_code=stock_in.gp_code,
            gp_name=stock_in.gp_name,
            curr_price=stock_in.curr_price,
            change_percent=stock_in.change_percent,
            change_amount=stock_in.change_amount,
            amplitude=stock_in.amplitude,
            volume_ratio=stock_in.volume_ratio,
            low=stock_in.low,
            high=stock_in.high,
            open=stock_in.open,
            prev_close=stock_in.prev_close,
            volume=stock_in.volume,
            amount=stock_in.amount,
            turnover_rate=stock_in.turnover_rate,
            pe_ttm=stock_in.pe_ttm,
            pb=stock_in.pb,
            total_market_cap=stock_in.total_market_cap,
            float_market_cap=stock_in.float_market_cap,
            create_time=stock_in.create_time,
            update_time=stock_in.update_time
        )
        self.db.add(db_stock)
        return db_stock

    def update_by_code(
        self,
        gp_code: str,
        update_data: Dict[str, str],
    ) -> Optional[bool]:
        """根据股票代码更新"""
        try:
            query = self.db.query(StockListInfo).filter(StockListInfo.gp_code == gp_code)
            affected_rows = query.update(update_data, synchronize_session="fetch")
            return affected_rows > 0
        except SQLAlchemyError as e:
            print(f"更新异常：{str(e)}，股票代码={gp_code}")
            raise

    def upsert(self, stock_in: StockListInfoCreate) -> StockListInfo:
        """插入或更新股票信息（根据股票代码匹配）"""
        existing = self.get_by_code(stock_in.gp_code)
        if existing:
            existing.gp_name = stock_in.gp_name
            existing.curr_price = stock_in.curr_price
            existing.change_percent = stock_in.change_percent
            existing.change_amount = stock_in.change_amount
            existing.amplitude = stock_in.amplitude
            existing.volume_ratio = stock_in.volume_ratio
            existing.low = stock_in.low
            existing.high = stock_in.high
            existing.open = stock_in.open
            existing.prev_close = stock_in.prev_close
            existing.volume = stock_in.volume
            existing.amount = stock_in.amount
            existing.turnover_rate = stock_in.turnover_rate
            existing.pe_ttm = stock_in.pe_ttm
            existing.pb = stock_in.pb
            existing.total_market_cap = stock_in.total_market_cap
            existing.float_market_cap = stock_in.float_market_cap
            existing.update_time = stock_in.update_time
            return existing
        else:
            return self.create(stock_in)

    def batch_create(self, stock_list: List[StockListInfoCreate]) -> List[StockListInfo]:
        """批量添加股票列表信息"""
        db_stocks = []
        for stock_in in stock_list:
            db_stock = StockListInfo(
                gp_code=stock_in.gp_code,
                gp_name=stock_in.gp_name,
                curr_price=stock_in.curr_price,
                change_percent=stock_in.change_percent,
                change_amount=stock_in.change_amount,
                amplitude=stock_in.amplitude,
                volume_ratio=stock_in.volume_ratio,
                low=stock_in.low,
                high=stock_in.high,
                open=stock_in.open,
                prev_close=stock_in.prev_close,
                volume=stock_in.volume,
                amount=stock_in.amount,
                turnover_rate=stock_in.turnover_rate,
                pe_ttm=stock_in.pe_ttm,
                pb=stock_in.pb,
                total_market_cap=stock_in.total_market_cap,
                float_market_cap=stock_in.float_market_cap,
                create_time=stock_in.create_time,
                update_time=stock_in.update_time
            )
            self.db.add(db_stock)
            db_stocks.append(db_stock)
        return db_stocks

    def count(self) -> int:
        """统计总数"""
        return self.db.query(func.count(StockListInfo.id)).scalar()
