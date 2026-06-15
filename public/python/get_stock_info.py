import random
import requests
import time
import json
import os
import hashlib
from datetime import datetime, timedelta

# 忽略SSL证书警告
requests.packages.urllib3.disable_warnings()

# 缓存配置
CACHE_DIR = os.path.join(os.path.dirname(__file__), 'cache')
CACHE_EXPIRE_MINUTES = 15

# 创建缓存目录
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)


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


def get_eastmoney_stock_data(stock_code):
    """东方财富接口，请求一次"""
    cached = get_cached_data(stock_code)
    if cached:
        return cached

    market_map = {
        '0': ['30', '002', '00'],
        '1': ['60', '68'],
        '8': ['8', '9']
    }
    secid = None
    for market_code, prefixes in market_map.items():
        if any(stock_code.startswith(p) for p in prefixes):
            secid = f"{market_code}.{stock_code}"
            break
    if not secid:
        print(f"❌ 股票代码{stock_code}格式错误，无法识别市场")
        return {}

    try:
        url = "https://push2.eastmoney.com/api/qt/stock/get"

        params = {
            'invt': '2',
            'fltt': '1',
            'cb': f'jQuery{int(time.time() * 1000)}_{int(random.random() * 10000000000000000)}',
            'fields': 'f57,f58,f43,f170,f169,f171,f50,f45,f44,f46,f60,f47,f48,f168,f162,f167,f116,f117',
            'secid': secid,
            'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
            '_': str(int(time.time() * 1000))
        }

        headers = {
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': f'https://quote.eastmoney.com/concept/sz{stock_code}.html',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        response = requests.get(url, params=params, headers=headers, verify=False, timeout=15)

        if response.status_code != 200:
            print(f"❌ 接口返回状态码: {response.status_code}")
            return {}

        jsonp_text = response.text.strip()
        start_idx = jsonp_text.find('{')
        end_idx = jsonp_text.rfind('}')

        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            print(f"❌ 接口返回无效数据")
            return {}

        json_str = jsonp_text[start_idx:end_idx + 1]
        stock_json = json.loads(json_str)

        if stock_json.get('rc') != 0:
            print(f"❌ 接口返回异常: {stock_json.get('msg', '无')}")
            return {}

        stock_data = stock_json.get('data', {})
        if not stock_data:
            print(f"❌ 接口无数据返回")
            return {}

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

        print(f"✅ 股票{stock_code}（{structured_data['股票名称']}）：数据获取成功")
        return structured_data

    except Exception as e:
        print(f"⚠️  请求失败: {str(e)}")
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
