import datetime
import sys
import os
from typing import List, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Body, File, UploadFile, Form
from sqlalchemy.orm import Session
from config import SessionLocal  # 导入数据库会话工厂
from datetime import date  # 避免与参数名冲突

from public.python.excel_to_json import excel_to_add, excel_to_update, update_bankuai, update_longhu, update_score, update_turnover_rate

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
        target_date: Optional[date] = None,  # 从查询参数接收日期（如?date=2025-11-07）
        db: Session = Depends(get_db),
):
    print(f"接收到的日期参数: {target_date}")
    repo = StockCollectionRepo(db)
    # 查询所有用户的收藏（共识）
    query = repo.db.query(StockCollection).filter(StockCollection.collect == 1)
    if target_date is not None:
        query = query.filter(StockCollection.date == target_date)
    stock_list = query.all()
    
    # 按股票名称分组，统计每个股票被不同用户收藏的次数，并记录最新创建时间
    from collections import defaultdict
    stock_users = defaultdict(set)
    stock_create_times = {}  # 记录每个股票最新的创建时间

    for item in stock_list:
        date_str = item.date.strftime('%Y-%m-%d') if item.date else None
        if date_str:
            stock_users[item.gp_name].add(item.user)
            # 保留最新的创建时间
            create_time_str = item.create_time.strftime('%Y-%m-%d %H:%M:%S') if item.create_time else None
            if create_time_str:
                if item.gp_name not in stock_create_times or create_time_str > stock_create_times[item.gp_name]:
                    stock_create_times[item.gp_name] = create_time_str

    # 构建返回数据，包含收藏次数统计和创建时间
    stock_data = []
    for gp_name, users in stock_users.items():
        collect_count = len(users)
        stock_data.append({
            'gp_name': gp_name,
            'date': date_str,
            'collect_count': collect_count,
            'create_time': stock_create_times.get(gp_name),
            'users': list(users)  # 可选：返回用户列表
        })

    # 按创建时间和收藏次数排序（优先按创建时间倒序）
    stock_data.sort(key=lambda x: (x.get('create_time') or '', -x['collect_count']), reverse=True)
    
    print(f"查询到的共识收藏数据（含统计）: {stock_data}")
    return stock_data

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
def get_stock_curr_info(gp_no: str, db: Session = Depends(get_db)):
    """获取实时个股详细信息（从数据库获取，避免爬虫风控）"""
    from services.stock_list_info_service import StockListInfoService
    
    # 去除股票代码后缀（如 .SH/.SZ）
    clean_code = gp_no.split('.')[0] if '.' in gp_no else gp_no
    
    service = StockListInfoService(db)
    stock = service.get_stock_info_by_code(clean_code)
    
    if not stock:
        raise HTTPException(status_code=404, detail=f"未找到股票代码 {clean_code} 的信息")
    
    # 将数据库字段转换为前端期望的中文字段名格式
    def parse_val(val, default=0):
        if val is None or val == '' or val == '-':
            return default
        return float(val)
    
    return {
        '股票代码': stock.gp_code,
        '股票名称': stock.gp_name,
        '涨跌幅(%)': parse_val(stock.change_percent),
        '换手率(%)': parse_val(stock.turnover_rate),
        '最新价': parse_val(stock.curr_price),
        '流通市值(亿)': parse_val(stock.float_market_cap),
        '最高': parse_val(stock.high),
        '最低': parse_val(stock.low),
        '开盘': parse_val(stock.open),
        '昨收': parse_val(stock.prev_close),
        '涨跌额': parse_val(stock.change_amount),
        '振幅': parse_val(stock.amplitude),
        '量比': parse_val(stock.volume_ratio),
        '成交量(万手)': parse_val(stock.volume),
        '成交额(亿元)': parse_val(stock.amount),
        '市盈率': parse_val(stock.pe_ttm),
        '市净率(%)': parse_val(stock.pb),
        '总市值': parse_val(stock.total_market_cap),
        '流通值': parse_val(stock.float_market_cap),
    }

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


@router.post("/stock/admin")
def stock_admin(
    zhangting_file: Optional[UploadFile] = File(None),
    huanshou_file: Optional[UploadFile] = File(None),
    bankuai_json: Optional[str] = Form(None),
    update_longhu_flag: Optional[str] = Form(None),
    update_score_flag: Optional[str] = Form(None),
    update_turnover_flag: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    import tempfile
    results = []
    
    # 处理涨停文件
    if zhangting_file:
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(zhangting_file.file.read())
            zhangting_path = f.name
        try:
            excel_to_add(zhangting_path)
            results.append("涨停文件处理成功")
        except Exception as e:
            results.append(f"涨停文件处理失败: {str(e)}")
        finally:
            os.unlink(zhangting_path)
    
    # 处理换手文件
    if huanshou_file:
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            f.write(huanshou_file.file.read())
            huanshou_path = f.name
        try:
            excel_to_update(huanshou_path)
            results.append("换手文件处理成功")
        except Exception as e:
            results.append(f"换手文件处理失败: {str(e)}")
        finally:
            os.unlink(huanshou_path)
    
    # 处理龙虎榜更新
    if update_longhu_flag and update_longhu_flag.lower() == 'yes':
        try:
            update_longhu()
            results.append("龙虎榜更新成功")
        except Exception as e:
            results.append(f"龙虎榜更新失败: {str(e)}")
    
    # 处理板块json
    if bankuai_json:
        import json
        try:
            bankuai_data = json.loads(bankuai_json)
            # 将json数据写入临时文件
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False, mode='w') as f:
                json.dump(bankuai_data, f)
                bankuai_path = f.name
            try:
                update_bankuai(bankuai_path)
                results.append("板块JSON处理成功")
            finally:
                os.unlink(bankuai_path)
        except json.JSONDecodeError:
            results.append("板块JSON格式无效")
        except Exception as e:
            results.append(f"板块JSON处理失败: {str(e)}")
    
    # 处理更新得分
    if update_score_flag and update_score_flag == 'yes':
        score_path = './stock_comment_em.xlsx'
        try:
            update_score(score_path)
            results.append("得分更新成功")
        except Exception as e:
            results.append(f"得分更新失败: {str(e)}")
    
    # 处理更新换手率
    if update_turnover_flag and update_turnover_flag.lower() == 'yes':
        try:
            update_turnover_rate()
            results.append("换手率更新成功")
        except Exception as e:
            results.append(f"换手率更新失败: {str(e)}")
    
    if not results:
        results.append("没有提供任何数据")
    
    return {"status": "success", "message": "; ".join(results)}
