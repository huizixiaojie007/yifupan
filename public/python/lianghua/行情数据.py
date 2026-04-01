"""
行情数据订阅模块
支持真实行情和模拟推送，保留集合竞价tick处理
"""
from typing import Callable, List, Dict, Optional
from datetime import datetime


# 全局变量：当前tick时间(用于模拟模式)
current_tick_time = None


class MarketDataSubscriber:
    """行情数据订阅器"""
    
    def __init__(self, use_real_market: bool = True, 
                 simulation_speed: float = 100.0,
                 simulation_path: str = ""):
        self.use_real_market = use_real_market
        self.simulation_speed = simulation_speed
        self.simulation_path = simulation_path  # 保留参数，但不再使用
        self.callback: Optional[Callable] = None
        
        # 导入xtquant
        try:
            from xtquant import xtdata
            self.xtdata = xtdata
        except ImportError:
            print("警告: xtquant未安装")
            self.xtdata = None
        
        # 模拟模式导入（使用集成的模拟器）
        # use_real_market=False 表示使用模拟推送
        if not use_real_market:
            try:
                from .行情模拟器 import quick_start
                self.quick_start = quick_start
            except ImportError:
                print("警告: 行情模拟器模块未找到")
                self.quick_start = None
        else:
            self.quick_start = None
    
    def subscribe(self, stocks: List[str], callback: Callable):
        """
        订阅股票行情
        
        Args:
            stocks: 股票代码列表
            callback: tick回调函数 callback(data: Dict[str, dict])
        """
        self.callback = callback
        
        if self.use_real_market:
            self._subscribe_real(stocks)  # True = 真实行情
        else:
            self._subscribe_simulation(stocks)  # False = 模拟推送
    
    def _subscribe_real(self, stocks: List[str]):
        """真实行情订阅（盘中启动时会先补足历史数据）"""
        if not self.xtdata:
            print("错误: xtdata未初始化")
            return
        
        # 检查是否在交易时间内
        from datetime import datetime
        now = datetime.now()
        current_time = now.strftime('%H%M')
        
        # 判断是否需要补足历史数据（盘中启动）
        is_intraday_start = False
        if '0925' <= current_time <= '1500':
            is_intraday_start = True
            print(f"\n{'='*80}")
            print(f"📊 检测到盘中启动（当前时间: {now.strftime('%H:%M:%S')}）")
            print(f"正在补足当日历史数据...")
            print(f"{'='*80}\n")
            
            # 补足当日历史分钟数据
            self._backfill_today_data(stocks)
        
        # 订阅实时行情
        self.xtdata.subscribe_whole_quote(stocks, callback=self._on_tick)
        
        if not is_intraday_start:
            print("\n📡 已订阅实时行情推送")
    
    def _backfill_today_data(self, stocks: List[str]):
        """补足当日历史数据 - 直接使用分钟K线,简单有效"""
        if not self.xtdata:
            return
        
        try:
            from datetime import datetime
            
            # 获取今日日期和时间
            now = datetime.now()
            today = now.strftime('%Y%m%d')
            start_time = today + '092500'  # 从9:25开始
            end_time = now.strftime('%Y%m%d%H%M%S')  # 到当前时间
            
            print(f"\n{'='*80}")
            print(f"📊 开始补足当日历史数据(分钟K线)")
            print(f"{'='*80}")
            print(f"时间: {start_time} -> {end_time}")
            print(f"股票: {len(stocks)} 只")
            print(f"{'='*80}\n")
            
            # 步骤1: 获取昨收价
            print("[1/4] 获取昨收价...")
            prev_close_dict = {}
            for stock_code in stocks:
                try:
                    full_tick = self.xtdata.get_full_tick([stock_code])
                    if full_tick and stock_code in full_tick:
                        prev_close_dict[stock_code] = full_tick[stock_code].get('lastClose', 0)
                except:
                    prev_close_dict[stock_code] = 0
            print(f"✅ 完成: {len([v for v in prev_close_dict.values() if v > 0])}/{len(stocks)}\n")
            
            # 步骤2: 下载1分钟K线
            print("[2/4] 下载1分钟K线...")
            self.xtdata.download_history_data2(
                stock_list=stocks,
                period='1m',
                start_time=start_time,
                end_time=end_time
            )
            print("✅ 完成\n")
            
            # 步骤3: 读取K线数据
            print("[3/4] 读取K线数据...")
            data = self.xtdata.get_market_data_ex(
                stock_list=stocks,
                period='1m',
                start_time=start_time,
                end_time=end_time
            )
            
            if not data:
                print("⚠️  未获取到数据\n")
                return
            print("✅ 完成\n")
            
            # 步骤4: 转换并推送
            print("[4/4] 转换并推送tick数据...")
            tick_count = 0
            
            for stock_code in stocks:
                if stock_code not in data or data[stock_code].empty:
                    continue
                
                df = data[stock_code]
                prev_close = prev_close_dict.get(stock_code, 0)
                
                # 每根K线转成1个tick
                for idx, row in df.iterrows():
                    tick_data = {
                        stock_code: {
                            'time': str(idx),
                            'lastPrice': row['close'],
                            'lastClose': prev_close,
                            'stockName': stock_code
                        }
                    }
                    
                    if self.callback:
                        self.callback(tick_data)
                    tick_count += 1
            
            print(f"✅ 完成: 推送 {tick_count} 条\n")
            print(f"{'='*80}")
            print(f"✅ 历史数据补足完成!")
            print(f"{'='*80}\n")
            
        except Exception as e:
            print(f"❌ 失败: {e}\n")
            import traceback
            traceback.print_exc()
    
    def _subscribe_simulation(self, stocks: List[str]):
        """模拟推送订阅"""
        if not self.quick_start:
            print("错误: 模拟推送未初始化")
            return
        
        self.quick_start(
            strategy_callback=self._on_tick,
            stocks=stocks,
            speed=self.simulation_speed,
            date=None,
            auto_wait=True
        )
    
    def _on_tick(self, data: Dict):
        """tick数据处理"""
        global current_tick_time
        
        # 更新全局tick时间(用于日志)
        if isinstance(data, dict):
            for stock_code, tick_info in data.items():
                if 'time' in tick_info:
                    current_tick_time = tick_info['time']
                    break
        
        # 回调用户函数
        if self.callback:
            self.callback(data)
    
    @staticmethod
    def is_auction_period(tick_time=None) -> bool:
        """
        判断是否在集合竞价期间
        注意: 9:25-9:30的tick需要特殊处理，不过滤
        """
        if tick_time:
            # 从tick时间判断
            time_str = str(tick_time)
            if len(time_str) >= 12:
                hhmm = time_str[8:12]
                # 9:15-9:24 为集合竞价(过滤)
                # 9:25-9:30 为有效tick(不过滤)
                return '0915' <= hhmm <= '0924'
        else:
            # 从系统时间判断
            now = datetime.now().time()
            auction_start = datetime.strptime("09:15", "%H:%M").time()
            auction_end = datetime.strptime("09:24", "%H:%M").time()
            return auction_start <= now <= auction_end
        
        return False
    
    @staticmethod
    def is_opening_tick(tick_time) -> bool:
        """
        判断是否为开盘集合竞价tick (9:25-9:30)
        这些tick包含重要的开盘价信息
        """
        time_str = str(tick_time)
        if len(time_str) >= 12:
            hhmm = time_str[8:12]
            return '0925' <= hhmm <= '0929'
        return False
