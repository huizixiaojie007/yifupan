"""
完整的股票数据自动补充模块
支持tick、分钟线、日线等多种周期数据的自动下载和补充
可作为模块导入，提供统一的数据下载接口
"""

import sys
import os

# 添加父目录到系统路径，以便导入template模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from xtquant import xtdata
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Optional, Union, Dict, Any

# 导入template中的模块
from template import StockPool
from template.配置模板 import THS_BLOCK_INI_PATH


class StockDataDownloader:
    """股票数据下载器类，支持多种周期数据的下载和补充"""
    
    # 支持的周期类型
    SUPPORTED_PERIODS = {
        'tick': 'tick',
        '1m': '1m',
        '5m': '5m',
        '15m': '15m',
        '30m': '30m',
        '60m': '60m',
        '1d': '1d',
        'daily': '1d',
        'day': '1d'
    }
    
    def __init__(self, verbose: bool = True):
        """
        初始化数据下载器
        
        Args:
            verbose: 是否显示详细进度信息
        """
        self.verbose = verbose
        
    def _on_progress(self, data: Dict[str, Any]) -> None:
        """
        进度回调函数（已废弃，改用单股循环显示进度）
        保留此方法以兼容可能的旧代码调用
        """
        pass
    
    def _calculate_time_range(self, days: int = 2, period: str = 'tick') -> tuple:
        """
        计算下载时间范围
        
        Args:
            days: 下载最近几天的数据
            period: 数据周期类型
            
        Returns:
            (start_time, end_time, query_start_time) 时间字符串元组
        """
        now = datetime.now()
        
        # 判断最近交易日
        if now.weekday() >= 5:  # 周六或周日
            last_trading_day = now - timedelta(days=now.weekday() - 4)  # 上周五
        else:
            last_trading_day = now - timedelta(days=1) if now.hour < 9 else now
        
        # 根据周期类型调整时间范围
        if period in ['tick', '1m', '5m', '15m', '30m', '60m']:
            # 分钟级及tick数据：带时分秒
            start_trading_day = last_trading_day - timedelta(days=days)
            start_time = start_trading_day.strftime('%Y%m%d') + '093000'
            end_time = last_trading_day.strftime('%Y%m%d') + '150000'
            query_start_time = last_trading_day.strftime('%Y%m%d') + '093000'
        else:
            # 日线数据：只需日期
            start_trading_day = last_trading_day - timedelta(days=days * 7)  # 日线数据多取一些
            start_time = start_trading_day.strftime('%Y%m%d')
            end_time = last_trading_day.strftime('%Y%m%d')
            query_start_time = start_time
            
        return start_time, end_time, query_start_time
    
    def download_data(self, 
                     stock_list: List[str], 
                     period: str = 'tick',
                     start_time: Optional[str] = None,
                     end_time: Optional[str] = None,
                     days: int = 2,
                     return_data: bool = True) -> Optional[Any]:
        """
        下载指定周期的股票数据
        
        Args:
            stock_list: 股票代码列表，如 ['000001.SZ', '600000.SH']
            period: 数据周期，支持 'tick', '1m', '5m', '15m', '30m', '60m', '1d'
            start_time: 开始时间，格式如 '20240101' 或 '20240101093000'
            end_time: 结束时间，格式同上
            days: 如果不指定start_time，则下载最近几天的数据
            return_data: 是否返回下载的数据
            
        Returns:
            如果return_data为True，返回下载的数据；否则返回None
        """
        if not stock_list:
            if self.verbose:
                print("股票列表为空，无需下载")
            return None
        
        # 标准化周期类型
        period = self.SUPPORTED_PERIODS.get(period.lower(), period)
        
        if period not in self.SUPPORTED_PERIODS.values():
            raise ValueError(f"不支持的周期类型: {period}，支持的类型: {list(self.SUPPORTED_PERIODS.keys())}")
        
        try:
            # 如果未指定时间，自动计算
            if start_time is None or end_time is None:
                calc_start, calc_end, query_start = self._calculate_time_range(days, period)
                start_time = start_time or calc_start
                end_time = end_time or calc_end
            else:
                query_start = start_time
            
            if self.verbose:
                print(f"\n开始下载{period}数据...")
                print(f"股票数量: {len(stock_list)}")
                print(f"时间范围: {start_time} - {end_time}")
                print(f"下载模式: 单股循环下载（更稳定）")
            
            # 使用download_history_data单股循环下载
            # 相比download_history_data2的优势：
            # 1. 单股下载更稳定，某股失败不影响其他股票
            # 2. 更精细的错误处理和进度控制
            # 3. 可以更灵活地控制每只股票的下载策略
            total = len(stock_list)
            success_count = 0
            fail_count = 0
            
            for idx, stock_code in enumerate(stock_list, 1):
                if self.verbose:
                    # 构造进度条
                    progress_percentage = (idx / total) * 100
                    bar_length = 40
                    filled_length = int(bar_length * idx // total)
                    bar = '█' * filled_length + '-' * (bar_length - filled_length)
                    print(f"股票代码: {stock_code} | [{bar}] {progress_percentage:.2f}% ({idx}/{total})", end='\r')
                
                try:
                    # 使用download_history_data下载单个股票
                    xtdata.download_history_data(
                        stock_code=stock_code,
                        period=period,
                        start_time=start_time,
                        end_time=end_time
                    )
                    success_count += 1
                except Exception as e:
                    fail_count += 1
                    if self.verbose:
                        print(f"\n警告: {stock_code} 下载失败 - {str(e)}")
                    continue
            
            if self.verbose:
                print()  # 换行
                print(f"{period}数据下载完成！成功: {success_count}, 失败: {fail_count}")
            
            # 如果需要返回数据
            if return_data:
                data = xtdata.get_market_data_ex(
                    stock_list=stock_list,
                    period=period,
                    start_time=query_start,
                    end_time=end_time
                )
                return data
            
            return None
            
        except Exception as e:
            if self.verbose:
                print(f"\n下载数据时出错: {str(e)}")
            return None
    
    def download_tick(self, stock_list: List[str], days: int = 2, **kwargs) -> Optional[Any]:
        """下载tick数据的便捷方法"""
        return self.download_data(stock_list, period='tick', days=days, **kwargs)
    
    def download_minute(self, stock_list: List[str], minute: int = 1, days: int = 2, **kwargs) -> Optional[Any]:
        """
        下载分钟线数据的便捷方法
        
        Args:
            stock_list: 股票列表
            minute: 分钟周期，支持 1, 5, 15, 30, 60
            days: 下载天数
        """
        period_map = {1: '1m', 5: '5m', 15: '15m', 30: '30m', 60: '60m'}
        period = period_map.get(minute, '1m')
        return self.download_data(stock_list, period=period, days=days, **kwargs)
    
    def download_daily(self, stock_list: List[str], days: int = 30, **kwargs) -> Optional[Any]:
        """下载日线数据的便捷方法"""
        return self.download_data(stock_list, period='1d', days=days, **kwargs)
    
    def batch_download(self, 
                      stock_list: List[str],
                      periods: Optional[List[str]] = None,
                      days: int = 2) -> Dict[str, Any]:
        """
        批量下载多个周期的数据
        
        Args:
            stock_list: 股票列表
            periods: 要下载的周期列表，如 ['tick', '1m', '5m', '1d']
            days: 下载天数
            
        Returns:
            字典，key为周期类型，value为对应数据
        """
        if periods is None:
            periods = ['tick', '1m', '5m', '1d']
        
        results = {}
        for period in periods:
            if self.verbose:
                print(f"\n{'='*60}")
            data = self.download_data(stock_list, period=period, days=days, return_data=True)
            results[period] = data
            
        return results


def download_tick_data_silently(stock_list: List[str], 
                                start_time: str, 
                                end_time: str) -> Optional[Any]:
    """
    静默下载tick数据（保留原有接口以兼容旧代码）
    
    Args:
        stock_list: 股票列表
        start_time: 开始时间
        end_time: 结束时间
        
    Returns:
        下载的tick数据
    """
    downloader = StockDataDownloader(verbose=True)
    return downloader.download_data(
        stock_list=stock_list,
        period='tick',
        start_time=start_time,
        end_time=end_time,
        return_data=True
    )


# 向后兼容的配置变量（已废弃，建议直接使用template.配置模板）
# 保留这些变量是为了兼容可能直接使用它们的旧代码
ini_path = THS_BLOCK_INI_PATH  # 从配置模板导入
block_name = "固态电池"  # 默认板块名称，可以在local_config.py中配置CUSTOM_BLOCK_NAME


def get_stock_list_from_block(block_name: str, ini_path: Optional[str] = None) -> List[str]:
    """
    从同花顺板块获取股票列表（新增便捷函数）
    
    Args:
        block_name: 板块名称
        ini_path: 同花顺配置文件路径，默认使用配置模板中的路径
        
    Returns:
        股票代码列表
    """
    if ini_path is None:
        ini_path = THS_BLOCK_INI_PATH
    
    stock_pool = StockPool(ini_path)
    stock_list = list(stock_pool.get_block(block_name))
    return stock_list


if __name__ == "__main__":
    """
    示例用法：演示如何使用本模块下载各种周期的数据
    """
    # 默认板块名称（可以通过命令行参数或配置文件修改）
    default_block_name = "固态电池"
    
    # 尝试从配置模板获取自定义板块名称
    try:
        from template.配置模板 import CUSTOM_BLOCK_NAME
        block_name = CUSTOM_BLOCK_NAME
        print(f"✓ 使用配置的板块: {block_name}")
    except (ImportError, AttributeError):
        block_name = default_block_name
        print(f"ℹ 使用默认板块: {block_name}")
    
    # 使用新的股票池管理模块获取股票列表
    print(f"\n从板块 [{block_name}] 获取股票列表...")
    print(f"配置文件: {THS_BLOCK_INI_PATH}")
    
    try:
        stock_list = get_stock_list_from_block(block_name)
    except Exception as e:
        print(f"❌ 获取股票列表失败: {e}")
        stock_list = []

    if not stock_list:
        print("未获取到股票列表")
        exit()

    print(f"获取到 {len(stock_list)} 只股票")
    
    # 创建下载器实例
    downloader = StockDataDownloader(verbose=True)
    
    # 示例1: 下载tick数据
    print("\n" + "="*60)
    print("示例1: 下载tick数据")
    print("="*60)
    tick_data = downloader.download_tick(stock_list, days=2, return_data=True)
    
    # 打印第一只股票的最近10个tick数据
    if tick_data and stock_list:
        first_stock = stock_list[0]
        
        if first_stock in tick_data:
            stock_tick_data = tick_data[first_stock]
            
            # tick数据是DataFrame格式
            if hasattr(stock_tick_data, 'tail'):
                print(f"\n{first_stock} 最近10个tick数据:")
                print("-" * 120)
                
                # 取最后10条
                last_10 = stock_tick_data.tail(10)
                
                # 打印关键字段
                print(f"{'时间':<20} {'最新价':<10} {'成交量':<12} {'成交额':<15} {'买一价':<10} {'卖一价':<10}")
                print("-" * 120)
                
                for idx, row in last_10.iterrows():
                    # 转换时间戳
                    from datetime import datetime
                    time_str = datetime.fromtimestamp(row['time']/1000).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 获取买一价和卖一价（可能是列表）
                    bid_price = row['bidPrice'][0] if isinstance(row['bidPrice'], list) and len(row['bidPrice']) > 0 else row['bidPrice']
                    ask_price = row['askPrice'][0] if isinstance(row['askPrice'], list) and len(row['askPrice']) > 0 else row['askPrice']
                    
                    print(f"{time_str:<20} "
                          f"{row['lastPrice']:<10.2f} "
                          f"{row['volume']:<12.0f} "
                          f"{row['amount']:<15.2f} "
                          f"{bid_price:<10.2f} "
                          f"{ask_price:<10.2f}")
                
                print("-" * 120)
                print(f"总共 {len(stock_tick_data)} 条tick数据")
            else:
                print(f"数据格式不正确: {type(stock_tick_data)}")
    
    # 示例2: 下载1分钟数据
    print("\n" + "="*60)
    print("示例2: 下载1分钟数据")
    print("="*60)
    downloader.download_minute(stock_list, minute=1, days=2, return_data=False)
    
    # 示例3: 下载5分钟数据
    print("\n" + "="*60)
    print("示例3: 下载5分钟数据")
    print("="*60)
    downloader.download_minute(stock_list, minute=5, days=2, return_data=False)
    
    # 示例4: 下载日线数据
    print("\n" + "="*60)
    print("示例4: 下载日线数据")
    print("="*60)
    downloader.download_daily(stock_list, days=30, return_data=False)
    
    # 示例5: 批量下载多个周期
    print("\n" + "="*60)
    print("示例5: 批量下载多个周期")
    print("="*60)
    # 取消注释以下代码来批量下载
    # results = downloader.batch_download(stock_list, periods=['tick', '1m', '5m', '1d'], days=2)
    
    print("\n所有数据下载完成！")



