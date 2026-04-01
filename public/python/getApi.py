from datetime import date, datetime, timedelta, time
import sqlalchemy

import tushare as ts
import akshare as ak
import requests
from requests.adapters import HTTPAdapter
import pandas as pd
from urllib3 import Retry
from functools import reduce

# 使用相对导入或完整路径
import sys
import os

from public.python.get_board_info_em import get_eastmoney_special_stock_list
from public.python.get_board_kline import get_board_kline
from public.python.get_stock_info import get_eastmoney_stock_data
from public.python.get_stock_of_board import get_stock_of_board_em
from public.python.get_time_sharing_em import get_eastmoney_stock_trend_sse

# 如果需要在同一目录下导入，确保当前目录在Python路径中
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from pathlib import Path  # 处理路径，兼容不同系统

pd.set_option('display.max_columns', None)  # 显示所有列


# ---------------------- 1. 核心配置（修正股票代码+日期计算）----------------------
STOCK_CODE = "600519.SH"  # 深市股票：sz+代码（000/300开头）
current_date = date.today()
days_ago = current_date - timedelta(days=60)
start_date = days_ago.strftime("%Y%m%d")  # 30天前（yyyymmdd）
# start_date = '20251021'  # 30天前（yyyymmdd）
end_date = current_date.strftime("%Y%m%d")  # 当前日期（yyyymmdd）

# print(f"当前日期（yyyymmdd）：{end_date}")
# print(f"30天前日期（yyyymmdd）：{start_date}")
def tushare_api(symbol, start_date, end_date):
    # ---------------------- 1. 初始化接口（替换为你的Token）----------------------
    # ts.set_token("7178d32c7fd62991a1e3efaebc8c81be311eef2e7aa652f9f79db700")  # 粘贴步骤2复制的Token
    # pro = ts.pro_api()  # 初始化API对象
    pro = ts.pro_api('7178d32c7fd62991a1e3efaebc8c81be311eef2e7aa652f9f79db700')
    df = pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
    # 转换为 JSON（前端友好格式）
    json_data = df.to_json(
        orient="records",  # 数组格式，每条数据为字典
        force_ascii=False,  # 保留中文（如日期格式）
        indent=2  # 格式化缩进，便于阅读
    )
    print('json_data: ', json_data)
    return json_data

def akshare_api_0():
    # ---------------------- 1. 调用A股实时行情接口 ----------------------
    # 接口说明：获取A股实时行情（新浪数据源），返回基础字段
    # stock_zh_a_spot_df = ak.stock_zh_a_spot()  # 全A股实时行情（返回约5000行数据）
    # stock_rank_lxsz_ths_df = ak.stock_rank_lxsz_ths()
    # print(stock_rank_lxsz_ths_df)
    # 指定股票的行情报价数据
    # stock_bid_ask_em_df = ak.stock_bid_ask_em(symbol="000592")
    # print(stock_bid_ask_em_df)
    current_date = date.today()  # 返回 datetime.date 对象（如：2025-11-22）
    start_date = current_date.strftime("%Y%m%d")  # 转换为字符串：20251122
    print("当前日期（yyyymmdd）：", start_date)

    # 2. 获取5天前的日期（格式：yyyymmdd）
    days_ago = current_date - timedelta(days=30)  # 日期减法，自动处理月份/年份切换
    end_date = days_ago.strftime("%Y%m%d")  # 转换为字符串：20251117
    print("30天前日期（yyyymmdd）：", end_date)
    # df = ak.stock_zh_a_hist(symbol="000592", period='daily', start_date=start_date, end_date=end_date)
    df = ak.stock_zh_a_daily(symbol="sz000592", start_date=start_date, end_date=end_date)
    df = df.fillna('')
    df = df.replace('NaN', '')
    # 遍历数据，添加板块、换手率、版型信息
    data = df.to_dict('records')
    print("data：", data)

# ---------------------- 2. 抗反爬配置（正确的会话+请求头）----------------------
# 创建全局会话（所有请求复用，携带统一请求头）
session = requests.Session()
# 正确设置会话级请求头（模拟浏览器，抗反爬）
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://finance.sina.cn/",  # 模拟新浪财经访问来源
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
})


# 重试装饰器（失败自动重试，兼容会话）
def retry_decorator(max_retries=3, delay=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    print(f"第{retries}次重试，错误：{str(e)}")
                    time.sleep(delay * (2 ** (retries - 1)))  # 间隔递增（2→4→8秒）
            raise Exception(f"重试{max_retries}次后仍失败")

        return wrapper

    return decorator


# ---------------------- 3. 核心接口调用（修复列名+数据清洗）----------------------
# @retry_decorator(max_retries=3, delay=2)
def get_stock_data(symbol, start_date, end_date):
    """获取30天历史行情，兼容列名+数据格式化"""
    # # 调用 AkShare 接口（复用全局会话，携带抗反爬头）
    # if(symbol.split('.')[1]=='SH'):
    #     code = str('sh' + symbol.split('.')[0])
    # else:
    #     code = str('sz' + symbol.split('.')[0])
    # # print('入参：', code, start_date, end_date)
    market_prefix = "sz"  # 默认深市
    if symbol.startswith(("00", "30", "20")):
        market_prefix = "sz"# 深市股票
    elif symbol.startswith(("60", "68", "90")):
        market_prefix = "sh"  # 沪市用sh，修复Referer错误
    elif symbol.startswith(("92", "93")):
        market_prefix = "bj"  # 沪市用sh，修复Referer错误
    else:
        print(f"❌ 股票代码[{symbol}]格式错误，仅支持A股6位数字代码")
        return []  # 返回空列表，避免None报错
    code = str(market_prefix + symbol.split('.')[0])

    df = ak.stock_zh_a_daily(
        symbol=code,
        start_date=start_date,
        end_date=end_date,
        adjust="qfq"  # 前复权（可选：hfq=后复权，none=不复权）
    )

    # 关键：兼容接口列名（"date" 或 "日期"）
    # print(f"接口返回列名：{df.columns.tolist()}")  # 调试用，查看实际列名
    if "date" not in df.columns:
        if "日期" in df.columns:
            df.rename(columns={"日期": "date"}, inplace=True)  # 中文转英文
        else:
            raise Exception(f"接口列名异常，无 'date' 或 '日期'，可用列：{df.columns.tolist()}")

    # 数据清洗：保留关键列+空值处理+格式优化
    key_columns = ["date", "open", "high", "low", "close", "volume", "amount", "pct_change"]
    # 过滤掉不存在的列（避免接口返回列变动导致报错）
    key_columns = [col for col in key_columns if col in df.columns]
    df = df[key_columns].fillna(0)  # 空值填充为0

    # 数值格式化（统一精度）
    for col in df.columns:
        if col in ["open", "high", "low", "close", "pct_change"]:
            df[col] = df[col].round(2)  # 价格/涨跌幅保留2位小数
        elif col in ["volume"]:
            df[col] = df[col].round(0)  # 成交量（手）取整
        elif col in ["amount"]:
            df[col] = df[col].round(2)  # 成交额（万元）保留2位小数

    return df.reset_index(drop=True)  # 重置索引，避免冗余


# ---------------------- 4. 主函数（整合逻辑+JSON输出）----------------------
def akshare_api_kline(symbol, start_date, end_date):
    try:
        df = get_stock_data(symbol, start_date, end_date)
        data = df.to_dict('records')
        # print('data:::', data)

        return data

    except Exception as e:
        print(f"\n获取失败：{str(e)}")
    finally:
        session.close()  # 关闭会话，释放连接

# ---------------------- 5. 批量获取K线数据（多线程版本）----------------------
def akshare_api_kline_batch(symbols, start_date, end_date, max_workers=8):
    """
    批量获取多个股票的 K 线数据（多线程版本）
    :param symbols: 股票代码列表，格式如 ['600519.SH', '000001.SZ']
    :param start_date: 开始日期，格式如 '20250101'
    :param end_date: 结束日期，格式如 '20251231'
    :param max_workers: 最大线程数，默认 8
    :return: 字典，key 为股票代码，value 为 K 线数据列表
    """
    import concurrent.futures
    from functools import partial
    
    result = {}
    
    # 定义单个股票的处理函数
    def process_single_symbol(symbol):
        """处理单个股票的 K 线数据获取"""
        try:
            # 为每个线程创建独立会话
            local_session = requests.Session()
            local_session.headers.update({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://finance.sina.cn/",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
            })
            
            # 获取股票数据
            df = get_stock_data(symbol, start_date, end_date)
            data = df.to_dict('records')
            return symbol, data
        except Exception as e:
            print(f"\n获取 {symbol} 失败：{str(e)}")
            return symbol, []
    
    # 使用线程池并行处理
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_symbol = {executor.submit(process_single_symbol, symbol): symbol for symbol in symbols}
        
        # 获取结果
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol, data = future.result()
            result[symbol] = data
    
    return result

# 日内分时
def time_sharing(symbol, start_date, end_date):

    data = get_eastmoney_stock_trend_sse(symbol=symbol.split('.')[0])
    return data

    # # if (symbol.split('.')[1] == 'SH'):
    # #     code = str('sh' + symbol.split('.')[0])
    # # if (symbol.split('.')[1] == 'SZ'):
    # #     code = str('sz' + symbol.split('.')[0])
    # # if (symbol.split('.')[1] == 'BJ'):
    # #     code = str('bj' + symbol.split('.')[0])
    #
    # #这个只返回大于400手的大单数据，不准，先不用
    # # stock_intraday_sina_df = ak.stock_intraday_sina(symbol=code, date=date)
    # start_date= start_date + " 09:30:00"
    # end_date= end_date + " 15:00:00"
    # stock_zh_a_hist_min_em_df = ak.stock_zh_a_hist_min_em(symbol=symbol.split('.')[0], start_date=start_date, end_date=end_date, period="1", adjust="")
    #
    # # 步骤1：同样先转换日期列为datetime类型
    # stock_zh_a_hist_min_em_df['时间'] = pd.to_datetime(stock_zh_a_hist_min_em_df['时间'])
    #
    # # 步骤2：获取最后一个日期天（纯日期）
    # last_pure_date = stock_zh_a_hist_min_em_df['时间'].dt.date.max()
    #
    # # 步骤3：构造该日期天的时间范围
    # start_time = pd.to_datetime(str(last_pure_date))  # 转为2025-12-19 00:00:00
    # end_time = pd.to_datetime(str(last_pure_date)) + pd.Timedelta(days=1, seconds=-1)  # 转为2025-12-19 23:59:59
    #
    # # 步骤4：筛选范围内的所有数据
    # last_day_data = stock_zh_a_hist_min_em_df[(stock_zh_a_hist_min_em_df['时间'] >= start_time) & (stock_zh_a_hist_min_em_df['时间'] <= end_time)]
    #
    # # 查看结果
    # print(f"日期天{last_pure_date}的所有数据：")
    # print('last_date_data:::', last_day_data)
    # return last_day_data.to_dict('records')

# 获取个股详情信息
def get_stock_detail(symbol):
    """获取个股详细信息"""
    try:
        if (symbol.split('.')[1] == 'SH'):
            code = str('SH' + symbol.split('.')[0])
        if (symbol.split('.')[1] == 'SZ'):
            code = str('SZ' + symbol.split('.')[0])
        # 获取实时行情
        stock_individual_spot_xq_df = ak.stock_individual_spot_xq(symbol=code)
        # stock_detail = stock_individual_spot_xq_df.to_dict('records')
        print('stock_detail:::', stock_individual_spot_xq_df)
        return stock_individual_spot_xq_df
    except Exception as e:
        print(f"获取个股详情失败：{e}")
        return None


def save_df_to_excel(
        df: pd.DataFrame,
        file_path: str,
        sheet_name: str = "sheet1",
        index: bool = False
) -> bool:
    """
    将DataFrame数据保存到Excel文件
    :param df: 要保存的DataFrame数据
    :param file_path: 保存路径（如：./stock_comment.xlsx）
    :param sheet_name: 工作表名称（默认sheet1）
    :param index: 是否保存DataFrame的索引列（默认False，避免冗余）
    :param encoding: 编码格式（默认utf-8）
    :return: 保存成功返回True，失败返回False
    """
    try:
        # 1. 校验DataFrame有效性
        if not isinstance(df, pd.DataFrame):
            print("错误：输入的不是有效的DataFrame数据！")
            return False
        if df.empty:
            print("警告：DataFrame为空，无需保存！")
            return False

        # 2. 处理保存路径（自动创建父目录）
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)  # 父目录不存在则创建

        # 3. 保存到Excel（使用openpyxl引擎，支持xlsx格式）
        df.to_excel(
            excel_writer=file_path_obj,
            sheet_name=sheet_name,
            index=index,
            engine="openpyxl"  # 指定引擎，避免依赖问题
        )

        print(f"数据保存成功！文件路径：{file_path_obj.absolute()}")
        return True

    except ImportError as e:
        print(f"错误：缺少Excel依赖库，请执行 pip install openpyxl 安装！详情：{e}")
        return False
    except PermissionError:
        print(f"错误：没有权限写入文件 {file_path}，请关闭Excel文件或检查权限！")
        return False
    except Exception as e:
        print(f"数据保存失败：{str(e)}")
        return False

def get_stock_fund_flow(symbol):
    if (symbol.split('.')[1] == 'SH'):
        code = str('1.' + symbol.split('.')[0])
    if (symbol.split('.')[1] == 'SZ'):
        code = str('0.' + symbol.split('.')[0])
        from . import get_fund_flow

    capital_flow_df = get_fund_flow.get_eastmoney_capital_flow(secid=code)
    return capital_flow_df

def get_stock_comment(symbol):
    # 1. 获取并标准化日期列（列名一致则跳过重命名）
    df_jg = ak.stock_comment_detail_zlkp_jgcyd_em(symbol=symbol)
    df_zh = ak.stock_comment_detail_zhpj_lspf_em(symbol=symbol)
    df_sc = ak.stock_comment_detail_scrd_focus_em(symbol=symbol)

    # 2. 批量合并（核心代码，一行搞定多表合并）
    df_list = [df_jg, df_zh, df_sc]
    final_df = reduce(lambda left, right: pd.merge(left, right, on='交易日', how='inner'), df_list)

    # 返回数组格式的数据，每条数据是一个字典
    return final_df.to_dict('records')

#获取停复盘信息
def get_tfp(date):
    try:
        # 1. 使用传入的date参数，不再写死日期
        stock_tfp_em_df = ak.stock_tfp_em(date=date)

        # 2. 先判断数据是否为空，避免后续筛选报错
        if stock_tfp_em_df.empty:
            print(f"日期{date}未获取到停复牌数据")
            return stock_tfp_em_df

        # 3. 筛选停牌原因为“拟筹划重大资产重组”的数据
        # 模糊匹配（应对可能的文字细微差异，如需精确匹配可去掉str.contains，改用==）
        filter_condition = stock_tfp_em_df["停牌原因"].str.contains("拟筹划重大资产重组", na=False)
        filtered_df = stock_tfp_em_df[filter_condition]

        # 4. 按预计复盘时间排序，日期由近到远
        if not filtered_df.empty and "预计复牌时间" in filtered_df.columns:
            # 将复牌时间转换为datetime类型
            filtered_df["预计复牌时间"] = pd.to_datetime(filtered_df["预计复牌时间"], errors='coerce')
            # 按复牌时间升序排序（近到远）
            filtered_df = filtered_df.sort_values(by="预计复牌时间", ascending=True).dropna(subset=["预计复牌时间"])

        # 5. 打印筛选后的结果
        print(f"日期{date}拟筹划重大资产重组的停牌数据：")
        print(filtered_df)

        return filtered_df.to_dict('records')

    except Exception as e:
        # 捕获异常，避免程序崩溃
        print(f"获取数据失败，错误信息：{e}")
        return None
#获取实时股票信息，东方财富
def get_stock_info_em(symbol):
    stock_code = symbol.split('.')[0]
    stock_info = get_eastmoney_stock_data(stock_code)
    return stock_info

#获取概念板块实时信息
def get_board_info_em(fs="m:90+t:3+f:!50"):
    board_data = get_eastmoney_special_stock_list(fs=fs)
    return board_data

#获取概念板块的股票列表
def get_board_stock_list(symbol):
    stock_data = get_stock_of_board_em(block_code=symbol)
    return stock_data

#获取概念板块的k线
def get_board_kline_em(secid):
    board_kline = get_board_kline(secid)
    return board_kline

if __name__ == '__main__':
    # get_board_info_em()
    get_board_stock_list('BK0695')
    # stock_board_concept_cons_em_df = ak.stock_board_concept_cons_em(symbol="融资融券")
    # print(stock_board_concept_cons_em_df)

    # stock_intraday_em_df = ak.stock_intraday_em(symbol="601212")
    # print(stock_intraday_em_df)
    # stock_bid_ask_em_df = ak.stock_bid_ask_em(symbol="603696")
    # print(stock_bid_ask_em_df)
    # get_tfp('20260114')
    # get_stock_comment('603696')
    # akshare_api_kline(symbol="001331.SZ", start_date="2025-12-18", end_date="2025-12-21")
    # get_stock_fund_flow('001331.SZ')

    # 打印所有包含 "sector" 和 "fund" 的接口（筛选板块资金流向相关）
    # stock_apis = [api for api in dir(ak) if "stock" in api and "sector" in api and "fund" in api]
    # print("AkShare 板块资金流向相关接口：", stock_apis)

    # #概念资金流
    # stock_fund_flow_concept_df = ak.stock_fund_flow_concept(symbol="即时") #choice of {“即时”, "3日排行", "5日排行", "10日排行", "20日排行"}
    # # data = stock_fund_flow_concept_df.to_dict('records')
    # # 转换为 JSON（前端友好格式）
    # data = stock_fund_flow_concept_df.to_json(
    #     orient="records",  # 数组格式，每条数据为字典
    #     force_ascii=False,  # 保留中文（如日期格式）
    #     indent=2  # 格式化缩进，便于阅读
    # )
    # print(data)

    #分时数据
    # stock_intraday_em_df = ak.stock_intraday_em(symbol="603696")
    # data = time_sharing('603386.SH', '2026-01-21','2026-01-26')
    # print(data)

    #每股收益
    # stock_profit_forecast_em_df = ak.stock_profit_forecast_em()
    # print(stock_profit_forecast_em_df)

    # #################千股千评#######################
    # # 1. 获取股票评论数据，综合得分
    # stock_comment_em_df = ak.stock_comment_em()
    # print("获取的DataFrame数据：")
    # print(stock_comment_em_df)
    #
    # # 2. 调用方法保存到Excel
    # # 保存路径可自定义，比如：D:/data/stock_comment_2025.xlsx
    # save_success = save_df_to_excel(
    #     df=stock_comment_em_df,
    #     file_path="./stock_comment_em.xlsx",  # 当前目录下的xlsx文件
    #     sheet_name="东方财富股票评论",  # 自定义工作表名
    #     index=False  # 不保存索引列
    # )
    # # 3. 验证结果
    # if save_success:
    #     # 可选：读取保存的Excel验证
    #     df_check = pd.read_excel("./stock_comment_em.xlsx", sheet_name="东方财富股票评论")
    #     print("\n验证保存结果（前5行）：")
    #     print(df_check.head())
    # #################千股千评#######################
    #
    # #获取实时行情数据
    # stock_zh_a_spot_df = ak.stock_zh_a_spot()
    # print(stock_zh_a_spot_df)

    #单次获取指定 symbol 的最新行情数据
    # get_stock_detail('600000.SH')
    # stock_individual_spot_xq_df = ak.stock_individual_spot_xq(symbol="XSHG600000")
    # print(stock_individual_spot_xq_df)

    # # 分时数据，注意：该接口返回的数据只有最近一个交易日的有开盘价，其他日期开盘价为 0
    # stock_zh_a_hist_min_em_df = ak.stock_zh_a_hist_min_em(symbol="000001", start_date="2025-12-18 09:30:00",
    #                                                       end_date="2025-12-21 15:00:00", period="1", adjust="")
    # print(stock_zh_a_hist_min_em_df)





