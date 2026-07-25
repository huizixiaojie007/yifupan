import sys
import os
from datetime import datetime

from sqlalchemy.orm import Session
from repositories.stock_list_info_repo import StockListInfoRepo
from schemas.stock_list_info import StockListInfoCreate, StockListInfoUpdate
from models.stock_list_info import StockListInfo


class StockListInfoService:
    """股票列表信息业务逻辑类"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = StockListInfoRepo(db)

    def add_stock_info(self, stock_in: StockListInfoCreate) -> StockListInfo:
        """添加股票信息"""
        db_stock = self.repo.create(stock_in)
        db_stock.create_time = datetime.now()
        db_stock.update_time = datetime.now()
        self.db.commit()
        self.db.refresh(db_stock)
        return db_stock

    def batch_add_stock_info(self, stock_list: list) -> list:
        """批量添加股票信息"""
        schema_list = [StockListInfoCreate(**item) for item in stock_list]
        db_stocks = self.repo.batch_create(schema_list)
        for db_stock in db_stocks:
            db_stock.create_time = datetime.now()
            db_stock.update_time = datetime.now()
        self.db.commit()
        return db_stocks

    def get_stock_info_by_id(self, id: int) -> StockListInfo:
        """根据ID获取股票信息"""
        return self.repo.get_by_id(id)

    def get_stock_info_by_code(self, gp_code: str) -> StockListInfo:
        """根据股票代码获取股票信息"""
        return self.repo.get_by_code(gp_code)

    def get_stock_info_by_name(self, gp_name: str) -> StockListInfo:
        """根据股票名称获取股票信息"""
        return self.repo.get_by_name(gp_name)

    def list_stock_info(self, skip: int = 0, limit: int = 100) -> list:
        """获取股票列表"""
        return self.repo.list_all(skip=skip, limit=limit)

    def search_by_code(self, gp_code: str, skip: int = 0, limit: int = 100) -> list:
        """根据股票代码模糊搜索"""
        return self.repo.list_by_code_like(gp_code, skip=skip, limit=limit)

    def search_by_name(self, gp_name: str, skip: int = 0, limit: int = 100) -> list:
        """根据股票名称模糊搜索"""
        return self.repo.list_by_name_like(gp_name, skip=skip, limit=limit)

    def update_stock_info(self, gp_code: str, update_data: dict) -> bool:
        """根据股票代码更新股票信息"""
        update_data['update_time'] = datetime.now()
        result = self.repo.update_by_code(gp_code, update_data)
        self.db.commit()
        return result

    def upsert_stock_info(self, stock_in: dict) -> StockListInfo:
        """插入或更新股票信息（根据股票代码匹配）"""
        schema = StockListInfoCreate(**stock_in)
        db_stock = self.repo.upsert(schema)
        if db_stock.create_time is None:
            db_stock.create_time = datetime.now()
        db_stock.update_time = datetime.now()
        self.db.commit()
        self.db.refresh(db_stock)
        return db_stock

    def batch_upsert_stock_info(self, stock_list: list) -> dict:
        """批量插入或更新股票信息"""
        success_count = 0
        fail_count = 0
        for stock_data in stock_list:
            try:
                schema = StockListInfoCreate(**stock_data)
                if not schema.gp_code:
                    fail_count += 1
                    continue
                db_stock = self.repo.upsert(schema)
                if db_stock.create_time is None:
                    db_stock.create_time = datetime.now()
                db_stock.update_time = datetime.now()
                success_count += 1
            except Exception as e:
                fail_count += 1
                print(f"处理股票失败: {stock_data.get('gp_code', '')} - {str(e)}")
        self.db.commit()
        return {
            'success': success_count,
            'fail': fail_count,
            'total': len(stock_list)
        }

    def sync_from_api(self) -> dict:
        """从东方财富API同步股票列表数据"""
        sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'public/python'))
        from get_stock_list_em import get_all_stock_list
        
        print("正在获取全部股票列表数据（分开获取各板块）...")
        stock_data_list = get_all_stock_list(page_size=100)
        
        if not stock_data_list:
            print("无股票数据，结束同步")
            return {
                'total_processed': 0,
                'success': 0,
                'fail': 0
            }
        
        mapped_list = []
        for stock in stock_data_list:
            # 将原始数值转换为字符串（数据库字段为String类型）
            def to_str(val):
                if val is None or val == '-':
                    return ''
                return str(val)
            
            mapped_stock = {
                'gp_code': to_str(stock.get('股票代码', '')),
                'gp_name': to_str(stock.get('股票名称', '')),
                'curr_price': to_str(stock.get('当前价', '')),
                'change_percent': to_str(stock.get('涨跌幅(%)', '')),
                'change_amount': to_str(stock.get('涨跌额', '')),
                'amplitude': to_str(stock.get('振幅', '')),
                'volume_ratio': to_str(stock.get('量比', '')),
                'low': to_str(stock.get('最低', '')),
                'high': to_str(stock.get('最高', '')),
                'open': to_str(stock.get('开盘', '')),
                'prev_close': to_str(stock.get('昨收', '')),
                'volume': to_str(stock.get('成交量(万手)', '')),
                'amount': to_str(stock.get('成交额(亿元)', '')),
                'turnover_rate': to_str(stock.get('换手率(%)', '')),
                'pe_ttm': to_str(stock.get('市盈率', '')),
                'pb': to_str(stock.get('市净率(%)', '')),
                'total_market_cap': to_str(stock.get('总市值', '')),
                'float_market_cap': to_str(stock.get('流通值', '')),
            }
            if mapped_stock['gp_code']:
                mapped_list.append(mapped_stock)
        
        # 分批处理，每批100条
        batch_size = 100
        total_success = 0
        total_fail = 0
        total_processed = 0
        
        for i in range(0, len(mapped_list), batch_size):
            batch = mapped_list[i:i+batch_size]
            result = self.batch_upsert_stock_info(batch)
            total_success += result['success']
            total_fail += result['fail']
            total_processed += result['total']
            print(f"处理批次 {i//batch_size + 1}: 成功 {result['success']}, 失败 {result['fail']}")
        
        return {
            'total_processed': total_processed,
            'success': total_success,
            'fail': total_fail
        }
