import random
import requests
import time
import json
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 忽略SSL证书警告
requests.packages.urllib3.disable_warnings()


# 重试装饰器
def retry_decorator(max_retries=4, delay=2):
    def decorator(func):
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    print(f"第{retries}次重试，错误：{str(e)}")
                    time.sleep(delay * (2 ** (retries - 1)))  # 间隔递增（2→4→8→16秒）
            print(f"⚠️  重试{max_retries}次后仍失败，返回空数据")
            return {}
        return wrapper
    return decorator


# 备用接口列表
ALTERNATIVE_HOSTS = [
    "push2.eastmoney.com",
    "push2his.eastmoney.com",
    "push2his01.eastmoney.com"
]


@retry_decorator(max_retries=3, delay=2)
def get_eastmoney_stock_data(stock_code):
    """
    爬取东方财富个股详情接口数据（终极修复：精准截取JSON内容）
    :param stock_code: 股票代码（如300063/600000）
    :return: dict - 结构化的股票数据，失败返回空字典
    """
    # ========== 1. 自动识别市场，生成secid ==========
    market_map = {
        '0': ['30', '002', '00'],  # 深市
        '1': ['60', '68'],  # 沪市
        '8': ['8', '9']  # 北交所
    }
    secid = None
    stock_prefix = stock_code[:3] if len(stock_code) >= 3 else stock_code[:1]
    for market_code, prefixes in market_map.items():
        if any(stock_code.startswith(p) for p in prefixes):
            secid = f"{market_code}.{stock_code}"
            break
    if not secid:
        print(f"❌ 股票代码{stock_code}格式错误，无法识别市场")
        return {}

    # 随机选择接口主机
    host = random.choice(ALTERNATIVE_HOSTS)
    url = f"https://{host}/api/qt/stock/get"
    
    # ========== 2. 接口配置 ==========
    params = {
        'invt': '2',
        'fltt': '1',
        'cb': f'jQuery{int(time.time() * 1000)}_{int(random.random() * 10000000000000000)}',
        'fields': 'f58,f734,f107,f57,f43,f59,f168,f169,f170,f152,f177,f111,f46,f60,f44,f45,f47,f260,f48,f261,f279,f277,f278,f288,f19,f17,f531,f15,f13,f11,f20,f18,f16,f14,f12,f39,f37,f35,f33,f31,f40,f38,f36,f34,f32,f211,f212,f213,f214,f215,f210,f209,f208,f207,f206,f161,f49,f171,f50,f86,f84,f85,f168,f108,f116,f167,f164,f162,f163,f92,f71,f117,f292,f51,f52,f191,f192,f262,f294,f181,f295,f269,f270,f256,f257,f285,f286,f120,f121,f122,f55,f174,f175,f135,f136,f301,f803',
        'secid': secid,
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'wbp2u': '|0|0|0|web',
        'dect': '1',
        '_': str(int(time.time() * 1000))
    }

    # 随机User-Agent
    user_agents = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    ]

    # 简化的请求头（减少被风控的概率）
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Connection': 'close',
        'Referer': f'https://quote.eastmoney.com/concept/sz{stock_code}.html',
        'User-Agent': random.choice(user_agents)
    }

    try:
        # 防风控延时（避免IP封禁）
        time.sleep(random.uniform(2, 5))

        # ========== 3. 发送请求 ==========
        # 创建带重试机制的Session
        session = requests.Session()
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET']
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.keep_alive = False  # 核心优化：禁用HTTP长连接

        # 发送请求（15秒超时，关闭SSL验证）
        response = session.get(
            url=url,
            params=params,
            headers=headers,
            verify=False,
            timeout=15
        )
        session.close()  # 立即关闭连接

        if response.status_code == 200:
            # ========== 终极修复：精准截取大括号内的JSON内容 ==========
            jsonp_text = response.text.strip()

            # 步骤1：找到第一个左大括号 { 的位置
            start_idx = jsonp_text.find('{')
            # 步骤2：找到最后一个右大括号 } 的位置
            end_idx = jsonp_text.rfind('}')

            # 检查是否找到有效位置
            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                print(f"❌ 股票{stock_code}：未找到有效的JSON内容，原始返回：{jsonp_text[:200]}")
                return {}

            # 步骤3：截取大括号内的所有内容（核心！）
            json_str = jsonp_text[start_idx:end_idx + 1]

            # 步骤4：解析JSON
            stock_json = json.loads(json_str)

            # 检查接口返回状态
            if stock_json.get('rc') != 0:
                print(f"❌ 股票{stock_code}：接口返回异常，rc={stock_json.get('rc')}，msg={stock_json.get('msg', '无')}")
                return {}

            stock_data = stock_json.get('data', {})
            if not stock_data:
                print(f"❌ 股票{stock_code}：接口无数据返回，完整返回：{stock_json}")
                return {}

            # ========== 字段映射（易读） ==========
            field_mapping = {
                'f57': '股票代码',
                'f58': '股票名称',
                'f43': '最新价',
                'f170': '涨跌幅(%)',
                'f169': '涨跌额',
                'f171': '振幅',
                'f50': '量比',
                'f45': '最低价',
                'f44': '最高价',
                'f46': '今开',
                'f60': '昨收',
                'f47': '成交量(手)',
                'f48': '成交额(亿)',
                'f168': '换手率(%)',
                'f162': '动态市盈率(TTM)',
                'f167': '市净率',
                'f116': '总市值(亿)',
                'f117': '流通市值(亿)'
            }

            structured_data = {}
            for field_code, field_name in field_mapping.items():
                structured_data[field_name] = stock_data.get(field_code, '-')

            print(f"✅ 股票{stock_code}（{structured_data['股票名称']}）：数据爬取成功")
            return structured_data

        else:
            print(f"❌ 股票{stock_code}：请求失败，状态码{response.status_code}")
            return {}

    except requests.exceptions.Timeout:
        print(f"❌ 股票{stock_code}：请求超时")
        return {}
    except Exception as e:
        print(f"❌ 股票{stock_code}：爬取出错，错误信息：{str(e)}")
        return {}


# ========== 调用测试 ==========
if __name__ == '__main__':
    # 测试300063
    stock_code = "002465"
    stock_info = get_eastmoney_stock_data(stock_code)
    if stock_info:
        print("\n📈 股票核心数据：")
        for key, value in stock_info.items():
            print(f"{key}：{value}")
