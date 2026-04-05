import datetime
import sys
import os
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query,Body
from sqlalchemy.orm import Session
from config import SessionLocal  # 导入数据库会话工厂
from datetime import date  # 避免与参数名冲突

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.stock_collection import StockCollection
from public.python.getApi import get_tfp, tushare_api, akshare_api_kline, time_sharing, get_stock_comment, \
    get_stock_info_em, get_board_info_em, get_board_stock_list, get_board_kline_em
from repositories.stock_collection_repo import StockCollectionRepo
from schemas.stock_collection import ToggleCollectionRes, ToggleCollectionReq, StockCollectionSchema
# 导入Pydantic模型（用于response_model）
from schemas.zhangting_info import ZhangtingInfoSchema, SectorResponse  # 关键：使用Pydantic模型
from repositories.zhangting_info_repo import ZhangtingInfoRepo
import akshare as ak

from services import stock_collection_service
from services.stock_collection_service import StockCollectionService


# 依赖：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(prefix="/api/zhangting")  # 前缀：/api/zhangting

# 接口定义：response_model 必须用 Pydantic 模型
@router.get("/info/list", response_model=List[ZhangtingInfoSchema], response_model_by_alias=False)  # 这里用ZhangtingInfoSchema
def get_zhangting_by_date(
    db: Session = Depends(get_db),
    date: Optional[date] = None,  # 从查询参数接收日期（如?date=2025-11-07）
    skip: int = 0,
    limit: int = 200
):
    repo = ZhangtingInfoRepo(db)
    data = repo.list_by_date(target_date=date, skip=skip, limit=limit)
    # print("get_zhangting_by_date：", data)
    return data

@router.get("/dates", response_model=List[str], response_model_by_alias=False)  # 这里用ZhangtingInfoSchema
def get_date_list(
    db: Session = Depends(get_db),
):
    repo = ZhangtingInfoRepo(db)
    # print("日期列表：", repo.get_date())

    return repo.get_date()

@router.get("/stock/detail", response_model=List[ZhangtingInfoSchema])
async def get_zhangting_by_name(
        gp_name: str,
        db: Session = Depends(get_db),
):
    repo = ZhangtingInfoRepo(db)
    stock_data = repo.list_by_name(gp_name=gp_name)
    # 若查询不到，返回空列表（而非None）
    if stock_data is None:
        return []  # 空列表符合List类型要求
    # 若查询到单条数据，包装成列表返回（如果模型要求列表）
    if isinstance(stock_data, dict):  # 假设单条数据是字典
        return [stock_data]
    return stock_data  # 若本身是列表，直接返回

# 定义接口：GET请求，接收股票代码参数（默认贵州茅台600519）
@router.get("/stock/kline")
def stock_api(gp_no: str, days: float):
    gp_no = gp_no
    # 1. 获取当前日期（格式：yyyymmdd）
    current_date = date.today()  # 返回 datetime.date 对象（如：2025-11-22）
    end_date = current_date.strftime("%Y%m%d")  # 转换为字符串：20251122

    # 2. 获取5天前的日期（格式：yyyymmdd）
    days_ago = current_date - datetime.timedelta(days=days)  # 日期减法，自动处理月份/年份切换
    start_date = days_ago.strftime("%Y%m%d")  # 转换为字符串：20251117

    df = akshare_api_kline(gp_no, start_date, end_date)
    return df

@router.get("/stock/time/sharing")
def stock_api_time_sharing(gp_no: str):
    """
    获取股票分时数据
    :param gp_no: 股票代码
    :param date: 日期字符串（格式示例：2025-12-08T10:30:00 或 2025-12-08）
    :return: 分时数据
    """
    try:
        # 步骤1：拆分T分隔符，提取纯日期部分（兼容带时间的日期字符串）
        # pure_date_str = date.split('T')[0]  # 例如：2025-12-08T10:30:00 → 2025-12-08

        current_date = date.today()
        # 额外定义 YYYYMMDD 格式的字符串（仅用于日志/展示）
        date_obj_yyyymmdd = current_date.strftime("%Y%m%d")
        # print('date_obj_yyyymmdd::', date_obj_yyyymmdd)

        # 接口需要的 YYYY-MM-DD 格式（直接从date对象转换）
        end_date = current_date.strftime("%Y-%m-%d")
        pre_date_obj = current_date - datetime.timedelta(days=5)
        pre_date = pre_date_obj.strftime("%Y-%m-%d")

        data = time_sharing(symbol=gp_no, start_date=pre_date, end_date=end_date)
        # print('stock_api_time_sharing:', data)
        return data

    except Exception as e:
        print(f"日期格式转换失败或获取分时数据异常：{e}")
        return []  # 异常时返回空列表，便于前端处理

@router.get("/stock/collect")
async def get_collect_by_user(
        user: str,
        date: Optional[date] = None,  # 从查询参数接收日期（如?date=2025-11-07）
        db: Session = Depends(get_db),
):
    print(f"接收到的用户参数: {user}")
    print(f"接收到的日期参数: {date}")
    repo = StockCollectionRepo(db)
    stock_data = repo.list_by_user_date(user=user, date=date)
    print(f"查询到的收藏数据: {stock_data}")
    # 若查询到单条数据，包装成列表返回（如果模型要求列表）
    return stock_data  # 若本身是列表，直接返回

@router.get("/stock/collect/consensus")
async def get_collect_consensus(
        date: Optional[date] = None,  # 从查询参数接收日期（如?date=2025-11-07）
        db: Session = Depends(get_db),
):
    print(f"接收到的日期参数: {date}")
    repo = StockCollectionRepo(db)
    # 查询所有用户的收藏（共识）
    query = repo.db.query(StockCollection).filter(StockCollection.collect == 1)
    if date is not None:
        query = query.filter(StockCollection.date == date)
    list = query.all()
    stock_data = []
    for item in list:
        stock_dict = {
            'id': item.id,
            'gp_name': item.gp_name,
            'user': item.user,
            'date': item.date.strftime('%Y-%m-%d') if item.date else None,
            'collect': item.collect,
            'create_time': item.create_time.strftime('%Y-%m-%d %H:%M:%S') if item.create_time else None,
            'update_time': item.update_time.strftime('%Y-%m-%d %H:%M:%S') if item.update_time else None
        }
        stock_data.append(stock_dict)
    print(f"查询到的共识收藏数据: {stock_data}")
    # 若查询到单条数据，包装成列表返回（如果模型要求列表）
    return stock_data  # 若本身是列表，直接返回

#更新收藏数据
@router.post("/stock/collect/toggle", summary="切换股票收藏状态（收藏/取消收藏）")
def toggle_collection(
    # POST 请求用 Body 参数接收（FastAPI 自动校验模型）
    req: StockCollectionSchema = Body(..., description="切换收藏参数"),
    db: Session = Depends(get_db),
):
    repo = StockCollectionRepo(db)
    result = repo.create(collect_in=req)
    return result

#获取题材信息
@router.get("/sectors", response_model=List[SectorResponse])
def get_sectors(db: Session = Depends(get_db)):
    repo = ZhangtingInfoRepo(db)
    sectors_data = repo.get_sectors()
    # print('sectors_data:::', sectors_data)
    # 若查询到单条数据，包装成列表返回（如果模型要求列表）
    return sectors_data  # 若本身是列表，直接返回

#获取题材中的所有股票
@router.get("/sector/stocks", response_model=List[ZhangtingInfoSchema])
async def get_stocks_by_sector(sector:str, db: Session = Depends(get_db)):
    repo = ZhangtingInfoRepo(db)
    stocks_data = repo.get_stocks_by_sector(sector)
    # print('stocks_data:::', stocks_data)
    # 若查询到单条数据，包装成列表返回（如果模型要求列表）
    return stocks_data  # 若本身是列表，直接返回

@router.get("/sector/count")
async def get_sector_count(db: Session = Depends(get_db)):
    repo = ZhangtingInfoRepo(db)
    data = repo.get_sector_count()
    return data

@router.get("/stock/detail")
def get_stock_detail(gp_no: str):
    """获取个股详细信息"""
    from public.python.getApi import get_stock_detail as get_stock_detail_func
    return get_stock_detail_func(gp_no)

@router.get("/stock/info")
def get_stock_curr_info(gp_no: str):
    """获取实时个股详细信息"""
    return get_stock_info_em(gp_no)

@router.get("/stock/fundflow")
def get_stock_fund_flow(gp_no: str):
    """获取个股资金流入情况"""
    # 转换股票代码格式：如600519.SH → 1.600519，000001.SZ → 0.000001
    if gp_no.endswith('.SH'):
        secid = f"1.{gp_no[:-3]}"
    elif gp_no.endswith('.SZ'):
        secid = f"0.{gp_no[:-3]}"
    else:
        # 默认按深市处理
        secid = f"0.{gp_no}"
    
    from public.python.get_fund_flow import get_eastmoney_capital_flow
    data = get_eastmoney_capital_flow(secid=secid)
    return data

@router.get("/stock/suspension")
def get_stock_suspension_data():
    """获取股票停牌信息"""
    date_time = date.today().strftime("%Y%m%d")
    data = get_tfp(date=date_time)
    return data

@router.get("/stock/comment")
def get_stock_comment_data(gp_no: str):
    symbol = gp_no.split('.')[0]
    data = get_stock_comment(symbol=symbol)
    return data

@router.get("/stock/kline/batch")
def get_stock_kline_batch_data(
    symbols: str,
    start_date: str,
    end_date: str,
    max_workers: int = 8
):
    """
    批量获取多个股票的K线数据（多线程版本）
    :param symbols: 股票代码列表，格式如 '600519.SH,000001.SZ'
    :param start_date: 开始日期，格式如 '20250101'
    :param end_date: 结束日期，格式如 '20251231'
    :param max_workers: 最大线程数，默认 8
    :return: 字典，key 为股票代码，value 为 K 线数据列表
    """
    # 将字符串转换为列表
    symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
    from public.python.getApi import akshare_api_kline_batch
    data = akshare_api_kline_batch(symbol_list, start_date, end_date, max_workers)
    return data

@router.get("/board/info")
def get_board_info(fs: str = "m:90+t:3+f:!50"):
    """获取板块列表信息"""
    print(f"接收到的fs参数: {fs}")
    result = get_board_info_em(fs=fs)
    print(f"返回的板块数据数量: {len(result) if result else 0}")
    return result

@router.get("/board/stock")
def get_board_stock(block_code):
    """获取板块中股票列表信息"""
    return get_board_stock_list(block_code)

@router.get("/board/kline")
def get_board_kline(secid):
    """获取板块的K线数据"""
    return get_board_kline_em(secid)

@router.get("/stocks/consecutive-limitup")
def get_consecutive_limitup_stocks(db: Session = Depends(get_db)):
    """获取连续涨停天数大于等于2的股票列表"""
    repo = ZhangtingInfoRepo(db)
    # 直接使用已经加载到内存中的数据
    return repo.consecutive_limitup_stocks



