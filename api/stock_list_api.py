from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from config import SessionLocal

from services.stock_list_info_service import StockListInfoService
from schemas.stock_list_info import StockListInfoSchema


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


router = APIRouter(prefix="/api/stock_list")


@router.post("/sync", response_model=Dict[str, Any])
def sync_stock_list(db: Session = Depends(get_db)):
    """
    从东方财富API同步股票列表数据（批量添加或更新）
    
    循环调用get_stock_list接口获取所有股票数据，
    如果数据库中已有记录则更新，没有则添加。
    
    返回:
        {
            "total_processed": 总处理数,
            "success": 成功数,
            "fail": 失败数
        }
    """
    service = StockListInfoService(db)
    try:
        result = service.sync_from_api()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upsert", response_model=StockListInfoSchema)
def upsert_stock_info(
    stock_data: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """
    插入或更新单条股票信息
    
    如果数据库中已有该股票代码的记录则更新，没有则添加。
    
    请求体示例:
        {
            "gp_code": "600000",
            "gp_name": "浦发银行",
            "curr_price": "8.50",
            "change_percent": "1.23",
            ...
        }
    """
    service = StockListInfoService(db)
    try:
        result = service.upsert_stock_info(stock_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch_upsert", response_model=Dict[str, Any])
def batch_upsert_stock_info(
    stock_list: list,
    db: Session = Depends(get_db)
):
    """
    批量插入或更新股票信息
    
    如果数据库中已有该股票代码的记录则更新，没有则添加。
    
    请求体示例:
        [
            {
                "gp_code": "600000",
                "gp_name": "浦发银行",
                ...
            },
            ...
        ]
    
    返回:
        {
            "success": 成功数,
            "fail": 失败数,
            "total": 总数
        }
    """
    service = StockListInfoService(db)
    try:
        result = service.batch_upsert_stock_info(stock_list)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info", response_model=StockListInfoSchema)
def get_stock_info(
    gp_code: Optional[str] = Query(None, description="股票代码"),
    gp_name: Optional[str] = Query(None, description="股票名称"),
    db: Session = Depends(get_db)
):
    """
    根据股票代码或股票名称获取股票信息
    
    参数:
        gp_code: 股票代码（优先）
        gp_name: 股票名称（当gp_code为空时使用）
    
    返回:
        股票信息对象
    """
    service = StockListInfoService(db)
    
    if gp_code:
        stock = service.get_stock_info_by_code(gp_code)
    elif gp_name:
        stock = service.get_stock_info_by_name(gp_name)
    else:
        raise HTTPException(status_code=400, detail="必须提供gp_code或gp_name参数")
    
    if not stock:
        raise HTTPException(status_code=404, detail="股票信息不存在")
    
    return stock


@router.get("/search", response_model=list)
def search_stock_info(
    keyword: str = Query(..., description="搜索关键词"),
    skip: int = Query(0, description="跳过条数"),
    limit: int = Query(20, description="返回条数"),
    db: Session = Depends(get_db)
):
    """
    根据股票代码或股票名称模糊搜索股票信息
    
    参数:
        keyword: 搜索关键词
        skip: 跳过条数
        limit: 返回条数
    
    返回:
        股票信息列表
    """
    service = StockListInfoService(db)
    
    # 先按代码搜索，没有结果再按名称搜索
    results = service.search_by_code(keyword, skip=skip, limit=limit)
    if not results:
        results = service.search_by_name(keyword, skip=skip, limit=limit)
    
    return results


@router.get("/list", response_model=list)
def list_stock_info(
    skip: int = Query(0, description="跳过条数"),
    limit: int = Query(100, description="返回条数"),
    db: Session = Depends(get_db)
):
    """
    获取股票列表
    
    参数:
        skip: 跳过条数
        limit: 返回条数
    
    返回:
        股票信息列表
    """
    service = StockListInfoService(db)
    return service.list_stock_info(skip=skip, limit=limit)


@router.get("/count", response_model=Dict[str, int])
def get_stock_count(db: Session = Depends(get_db)):
    """
    获取股票总数
    
    返回:
        {"count": 总数}
    """
    service = StockListInfoService(db)
    count = service.get_stock_count()
    return {"count": count}
