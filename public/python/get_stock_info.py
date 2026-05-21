import random
import requests
import time
import json
import os
import hashlib
from datetime import datetime, timedelta
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 忽略SSL证书警告
requests.packages.urllib3.disable_warnings()

# 缓存配置
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
CACHE_EXPIRE_MINUTES = 15

# 创建缓存目录
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# 请求间隔配置
MIN_REQUEST_DELAY = 5
MAX_REQUEST_DELAY = 10

# 最后请求时间记录
_last_request_time = 0

# 代理IP列表（需要替换为实际可用的代理）
# 格式: [{"http": "http://ip:port", "https": "https://ip:port"}, ...]
PROXY_LIST = [
    # 示例代理（需要替换为实际可用的代理）
    # {"http": "http://123.123.123.123:8080", "https": "https://123.123.123.123:8080"},
    # {"http": "http://111.111.111.111:3128", "https": "https://111.111.111.111:3128"},
]

# 是否启用代理模式
USE_PROXY = len(PROXY_LIST) > 0


def get_cache_path(stock_code):
    code_hash = hashlib.md5(stock_code.encode()).hexdigest()
    return os.path.join(CACHE_DIR, f"{code_hash}.json")


def get_cached_data(stock_code):
    cache_path = get_cache_path(stock_code)
    if not os.path.exists(cache_path):
        return None
    
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        cache_time = datetime.fromisoformat(data['timestamp'])
        if datetime.now() - cache_time > timedelta(minutes=CACHE_EXPIRE_MINUTES):
            return None
        
        print(f"📦 使用缓存数据: {stock_code}")
        return data['stock_info']
    except Exception as e:
        print(f"⚠️  读取缓存失败: {e}")
        return None


def save_cache_data(stock_code, stock_info):
    try:
        cache_path = get_cache_path(stock_code)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'stock_info': stock_info
            }, f, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️  保存缓存失败: {e}")


def rate_limit():
    global _last_request_time
    now = time.time()
    time_since_last = now - _last_request_time
    
    if time_since_last < MIN_REQUEST_DELAY:
        wait_time = random.uniform(MIN_REQUEST_DELAY - time_since_last, MAX_REQUEST_DELAY - time_since_last)
        print(f"⏳ 等待 {wait_time:.1f} 秒后继续...")
        time.sleep(wait_time)
    
    _last_request_time = time.time()


def get_random_proxy():
    """随机获取一个代理"""
    if not USE_PROXY or len(PROXY_LIST) == 0:
        return None
    return random.choice(PROXY_LIST)


def get_sina_stock_data(stock_code, proxy=None):
    """备用数据源：新浪财经接口"""
    try:
        if stock_code.startswith('6'):
            sina_code = 'sh' + stock_code
        else:
            sina_code = 'sz' + stock_code
        
        url = f"http://hq.sinajs.cn/list={sina_code}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'http://finance.sina.com.cn/'
        }
        
        response = requests.get(url, headers=headers, proxies=proxy, timeout=15)
        if response.status_code != 200:
            return None
        
        content = response.text
        if 'var hq_str' not in content:
            return None
        
        start_idx = content.find('"') + 1
        end_idx = content.rfind('"')
        data_str = content[start_idx:end_idx]
        parts = data_str.split(',')
        
        if len(parts) < 32:
            return None
        
        return {
            '股票代码': stock_code,
            '股票名称': parts[0],
            '最新价': parts[1],
            '涨跌幅(%)': round((float(parts[1]) - float(parts[2])) / float(parts[2]) * 100, 2),
            '涨跌额': round(float(parts[1]) - float(parts[2]), 2),
            '振幅': '-',
            '量比': '-',
            '最低价': parts[5],
            '最高价': parts[4],
            '今开': parts[1],
            '昨收': parts[2],
            '成交量(手)': round(float(parts[8]) / 100, 2),
            '成交额(亿)': round(float(parts[9]) / 100000000, 2),
            '换手率(%)': '-',
            '动态市盈率(TTM)': '-',
            '市净率': '-',
            '总市值(亿)': '-',
            '流通市值(亿)': '-'
        }
    except Exception as e:
        print(f"⚠️  新浪接口失败: {e}")
        return None


EASTMONEY_HOSTS = [
    "push2his.eastmoney.com",
    "push2his01.eastmoney.com",
    "push2.eastmoney.com"
]


def get_eastmoney_stock_data(stock_code):
    """主数据源：东方财富接口"""
    cached = get_cached_data(stock_code)
    if cached:
        return cached
    
    rate_limit()
    
    market_map = {
        '0': ['30', '002', '00'],
        '1': ['60', '68'],
        '8': ['8', '9']
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
    
    # 获取代理（如果启用）
    proxy = get_random_proxy()
    if proxy:
        print(f"🌐 使用代理: {proxy.get('http', proxy.get('https', '无'))}")
    
    # 遍历所有接口主机尝试
    for host_idx, host in enumerate(EASTMONEY_HOSTS):
        try:
            print(f"🔍 尝试接口 {host_idx + 1}/{len(EASTMONEY_HOSTS)}: {host}")
            
            url = f"https://{host}/api/qt/stock/get"
            
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
            
            user_agents = [
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
            ]
            
            headers = {
                'Accept': '*/*',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                'Connection': 'close',
                'Referer': f'https://quote.eastmoney.com/concept/sz{stock_code}.html',
                'User-Agent': random.choice(user_agents)
            }
            
            session = requests.Session()
            retry = Retry(total=2, backoff_factor=2, status_forcelist=[500, 502, 503], allowed_methods=['GET'])
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)
            session.keep_alive = False
            
            response = session.get(url, params=params, headers=headers, proxies=proxy, verify=False, timeout=15)
            session.close()
            
            if response.status_code != 200:
                print(f"❌ 接口 {host} 返回状态码: {response.status_code}")
                continue
            
            jsonp_text = response.text.strip()
            start_idx = jsonp_text.find('{')
            end_idx = jsonp_text.rfind('}')
            
            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                print(f"❌ 接口 {host} 返回无效数据")
                continue
            
            json_str = jsonp_text[start_idx:end_idx + 1]
            stock_json = json.loads(json_str)
            
            if stock_json.get('rc') != 0:
                print(f"❌ 接口 {host} 返回异常: {stock_json.get('msg', '无')}")
                continue
            
            stock_data = stock_json.get('data', {})
            if not stock_data:
                print(f"❌ 接口 {host} 无数据返回")
                continue
            
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
            
            save_cache_data(stock_code, structured_data)
            
            print(f"✅ 股票{stock_code}（{structured_data['股票名称']}）：数据爬取成功（使用{host}）")
            return structured_data
            
        except Exception as e:
            print(f"⚠️  接口 {host} 请求失败: {str(e)}")
            continue
    
    # 尝试新浪备用接口（带代理）
    print("🔄 尝试备用数据源：新浪财经")
    sina_data = get_sina_stock_data(stock_code, proxy)
    if sina_data:
        save_cache_data(stock_code, sina_data)
        print(f"✅ 股票{stock_code}：使用备用数据源获取成功")
        return sina_data
    
    # 尝试不使用代理（如果之前使用了代理）
    if proxy:
        print("🔄 尝试不使用代理直接访问")
        return get_eastmoney_stock_data_no_proxy(stock_code)
    
    print(f"❌ 所有数据源都失败，返回空数据")
    return {}


def get_eastmoney_stock_data_no_proxy(stock_code):
    """不带代理的请求（作为最后的尝试）"""
    cached = get_cached_data(stock_code)
    if cached:
        return cached
    
    market_map = {
        '0': ['30', '002', '00'],
        '1': ['60', '68'],
        '8': ['8', '9']
    }
    secid = None
    stock_prefix = stock_code[:3] if len(stock_code) >= 3 else stock_code[:1]
    for market_code, prefixes in market_map.items():
        if any(stock_code.startswith(p) for p in prefixes):
            secid = f"{market_code}.{stock_code}"
            break
    if not secid:
        return {}
    
    try:
        url = f"https://push2his.eastmoney.com/api/qt/stock/get"
        
        params = {
            'invt': '2',
            'fltt': '1',
            'cb': f'jQuery{int(time.time() * 1000)}_{int(random.random() * 10000000000000000)}',
            'fields': 'f57,f58,f43,f170,f169,f45,f44,f46,f60,f47,f48,f168,f162,f167,f116,f117',
            'secid': secid,
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            '_': str(int(time.time() * 1000))
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://quote.eastmoney.com/'
        }
        
        response = requests.get(url, params=params, headers=headers, verify=False, timeout=10)
        
        if response.status_code == 200:
            jsonp_text = response.text.strip()
            start_idx = jsonp_text.find('{')
            end_idx = jsonp_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
                json_str = jsonp_text[start_idx:end_idx + 1]
                stock_json = json.loads(json_str)
                
                if stock_json.get('rc') == 0:
                    stock_data = stock_json.get('data', {})
                    if stock_data:
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
                        
                        save_cache_data(stock_code, structured_data)
                        return structured_data
        return {}
    except Exception:
        return {}


if __name__ == '__main__':
    test_codes = ["002465", "603067", "300063"]
    
    for code in test_codes:
        print(f"\n{'='*50}")
        print(f"测试股票: {code}")
        print('='*50)
        
        stock_info = get_eastmoney_stock_data(code)
        if stock_info:
            print("\n📈 股票核心数据：")
            for key, value in stock_info.items():
                print(f"{key}：{value}")
        else:
            print(f"\n❌ 未能获取股票 {code} 数据")
        
        time.sleep(2)
