"""
行情模拟推送器
功能: 将历史tick数据模拟成实时推送，集成到template包中
"""
import time
import threading
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Callable, Dict, Optional, List


class MarketDataSimulator:
    """行情推送模拟器"""

    def __init__(self):
        """初始化模拟器"""
        self.tick_data = {}              # 存储tick数据 {股票代码: DataFrame}
        self.callbacks = []              # 回调函数列表
        self.is_running = False          # 运行状态标志
        self.current_index = {}          # 每只股票当前推送的索引位置
        self.push_thread = None          # 推送线程对象
        self.speed = 1.0                 # 推送速度倍数(1.0=实际速度)

    def load_data(self, tick_data: Dict):
        """
        加载tick数据

        Args:
            tick_data: {股票代码: DataFrame}格式的tick数据
        """
        self.tick_data = tick_data
        for stock_code in tick_data.keys():
            self.current_index[stock_code] = 0
        print(f"已加载{len(tick_data)}只股票的tick数据")

    def subscribe(self, callback: Callable):
        """
        订阅行情推送

        Args:
            callback: 回调函数，接收参数为{股票代码: tick数据字典}
        """
        self.callbacks.append(callback)
        print(f"已添加回调函数，当前订阅数:{len(self.callbacks)}")

    def set_speed(self, speed: float):
        """
        设置推送速度

        Args:
            speed: 速度倍数，1.0=正常速度，2.0=2倍速，0.5=半速
        """
        self.speed = speed
        print(f"推送速度已设置为:{speed}x")

    def start(self):
        """启动行情推送"""
        if self.is_running:
            print("模拟器已在运行中")
            return

        self.is_running = True
        self.push_thread = threading.Thread(target=self._push_loop)
        self.push_thread.daemon = True
        self.push_thread.start()
        print("行情推送已启动")

    def stop(self):
        """停止行情推送"""
        self.is_running = False
        if self.push_thread:
            self.push_thread.join(timeout=1)
        print("行情推送已停止")

    def _push_loop(self):
        """
        推送循环(在独立线程中运行)
        按全局时间顺序推送所有股票的tick数据
        """
        print("正在合并和排序所有股票的tick数据...")
        all_ticks = []

        # 合并所有股票的tick数据
        for stock_code, df in self.tick_data.items():
            for idx in range(len(df)):
                row = df.iloc[idx]
                tick_time = row.name

                # 转换为datetime对象
                if isinstance(tick_time, str):
                    tick_time = pd.to_datetime(tick_time)

                all_ticks.append({
                    'stock_code': stock_code,
                    'time': tick_time,
                    'row': row,
                    'df_index': idx
                })

        # 按时间排序
        all_ticks.sort(key=lambda x: x['time'])
        total_ticks = len(all_ticks)

        print(f"合并完成! 共{total_ticks}条tick数据，按时间排序推送")
        print(f"时间范围: {all_ticks[0]['time']} 到 {all_ticks[-1]['time']}")
        print()

        # 按时间顺序推送
        last_progress_report = 0
        start_real_time = time.time()
        first_tick_time = all_ticks[0]['time']

        for i, tick_item in enumerate(all_ticks):
            if not self.is_running:
                break

            stock_code = tick_item['stock_code']
            tick_time = tick_item['time']
            row = tick_item['row']

            # 计算时间差
            time_offset = (tick_time - first_tick_time).total_seconds()

            # 根据速度倍数计算等待时间
            target_real_time = start_real_time + (time_offset / self.speed)

            # 等待到目标时间
            current_real_time = time.time()
            wait_seconds = target_real_time - current_real_time

            if wait_seconds > 0:
                time.sleep(wait_seconds)

            # 推送这条tick
            self._push_tick(stock_code, row)

            # 显示进度
            pushed_ticks = i + 1
            if pushed_ticks - last_progress_report >= 1000:
                progress = pushed_ticks / total_ticks * 100
                print(f"推送进度: {pushed_ticks}/{total_ticks} ({progress:.1f}%) | "
                      f"当前时间: {tick_time}")
                last_progress_report = pushed_ticks

        # 推送完成
        print("\n" + "=" * 60)
        print("所有股票tick数据推送完毕")
        print("=" * 60)
        self.is_running = False

    def _push_tick(self, stock_code: str, tick_row):
        """
        推送单条tick数据到所有订阅者

        Args:
            stock_code: 股票代码
            tick_row: tick数据行
        """
        # 转换为字典格式(模拟xtquant推送格式)
        tick_dict = {}

        # 提取所有字段
        for key in tick_row.index:
            if key != tick_row.name:
                tick_dict[key] = tick_row[key]

        # 添加时间字段
        tick_dict['time'] = tick_row.name

        # 兼容处理：展开数组字段
        for array_field in ['askPrice', 'bidPrice', 'askVol', 'bidVol']:
            if array_field in tick_dict:
                array_data = tick_dict[array_field]
                if hasattr(array_data, '__len__') and not isinstance(array_data, str):
                    prefix = array_field.replace('Price', '').replace('Vol', 'Vol')
                    for i, value in enumerate(array_data[:5], 1):
                        tick_dict[f'{prefix}{i}'] = value

        # 构造推送数据
        push_data = {stock_code: tick_dict}

        # 调用所有回调函数
        for callback in self.callbacks:
            try:
                callback(push_data)
            except Exception as e:
                print(f"回调函数执行出错: {e}")


class TickDataDownloader:
    """Tick数据下载器"""

    def __init__(self):
        """初始化下载器"""
        try:
            from xtquant import xtdata
            self.xtdata = xtdata
        except ImportError:
            print("警告: xtquant未安装")
            self.xtdata = None

    def _get_recent_trading_day(self) -> str:
        """
        获取最近的交易日

        Returns:
            日期字符串，格式'YYYYMMDD'
        """
        # 导入交易日历
        from .交易日历 import trading_calendar
        
        now = datetime.now()

        # 如果是早上9:30之前，使用前一交易日
        if now.hour < 9 or (now.hour == 9 and now.minute < 30):
            start_date = now - timedelta(days=1)
        else:
            start_date = now

        # 获取最近的交易日
        last_trading_day = trading_calendar.get_last_trading_day(start_date)
        return last_trading_day.strftime('%Y%m%d')

    def download_tick_data(self, stock_list: List[str], date_str: Optional[str] = None) -> Dict:
        """
        下载指定股票列表的tick数据

        Args:
            stock_list: 股票代码列表，如['000001.SZ', '600000.SH']
            date_str: 日期字符串，格式'YYYYMMDD'，默认为最近交易日

        Returns:
            {股票代码: DataFrame} 格式的tick数据字典
        """
        if not self.xtdata:
            print("错误: xtdata未初始化")
            return {}

        # 如果没有指定日期，获取最近交易日
        if date_str is None:
            date_str = self._get_recent_trading_day()
            print(f"未指定日期，自动使用最近交易日: {date_str}")

        # 构造时间范围
        start_date = datetime.strptime(date_str, '%Y%m%d') - timedelta(days=2)
        start_time_download = start_date.strftime('%Y%m%d') + '091500'
        end_time = f"{date_str}150000"
        start_time_get = f"{date_str}091500"

        print(f"开始下载tick数据: {date_str}")
        print(f"股票数量: {len(stock_list)}")

        # 下载到本地
        print("正在下载数据到本地...")
        self.xtdata.download_history_data2(
            stock_list=stock_list,
            period="tick",
            start_time=start_time_download,
            end_time=end_time,
            callback=self._on_progress
        )

        # 从本地获取数据
        print("正在从本地读取数据...")
        tick_data = self.xtdata.get_market_data_ex(
            stock_list=stock_list,
            period="tick",
            start_time=start_time_get,
            end_time=end_time
        )

        print(f"\n下载完成! 共获取{len(tick_data)}只股票的数据")

        # 检查数据
        has_data = False
        for stock_code, df in tick_data.items():
            if df is not None and len(df) > 0:
                print(f"✓ {stock_code}: {len(df)}条tick数据")
                has_data = True
            else:
                print(f"✗ {stock_code}: 无数据")

        if not has_data:
            print("\n【警告】未获取到任何tick数据!")
            print("可能原因:")
            print(f"1. {date_str} 不是交易日")
            print("2. 数据尚未生成")
            print("3. 股票代码不正确")

        return tick_data

    def _on_progress(self, data: Dict):
        """下载进度回调"""
        total = data.get('total', 0)
        finished = data.get('finished', 0)
        stock_code = data.get('stockcode', '')

        progress = (finished / total * 100) if total > 0 else 0
        bar_length = 40
        filled = int(bar_length * finished / total) if total > 0 else 0
        bar = '█' * filled + '-' * (bar_length - filled)

        print(f"{stock_code} [{bar}] {progress:.1f}% ({finished}/{total})", end='\r')

        if finished == total:
            print()


def quick_start(strategy_callback: Callable,
                stocks: Optional[List[str]] = None,
                speed: float = 10.0,
                date: Optional[str] = None,
                auto_wait: bool = True):
    """
    快速启动行情推送模拟器

    Args:
        strategy_callback: 策略回调函数，接收data参数
        stocks: 股票列表，如['000001.SZ', '600000.SH']
        speed: 推送速度倍数（默认10倍速）
        date: 指定日期如'20251030'（None=最近交易日）
        auto_wait: 是否自动等待推送完成（默认True）

    Returns:
        MarketDataSimulator - 模拟器实例
    """
    print("=" * 60)
    print("快速启动行情推送模拟器".center(60))
    print("=" * 60)

    if not stocks:
        raise ValueError("必须指定 stocks 参数")

    # 下载数据
    downloader = TickDataDownloader()
    print(f"\n📥 下载tick数据...")
    tick_data = downloader.download_tick_data(stocks, date_str=date)

    if not tick_data or len(tick_data) == 0:
        print("❌ 未下载到数据，退出")
        return None

    # 创建模拟器
    print(f"\n🚀 创建模拟器 (速度: {speed}倍速)")
    simulator = MarketDataSimulator()
    simulator.load_data(tick_data)
    simulator.subscribe(strategy_callback)
    simulator.set_speed(speed)

    # 启动推送
    print(f"\n▶️  开始推送行情数据...")
    print("=" * 60 + "\n")
    simulator.start()

    # 自动等待
    if auto_wait:
        try:
            while simulator.is_running:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n\n⏹️  用户中断，停止推送")
            simulator.stop()

        print("\n" + "=" * 60)
        print("✅ 推送完成".center(60))
        print("=" * 60)

    return simulator
