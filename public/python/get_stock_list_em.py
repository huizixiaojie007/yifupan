import random
import time
import json
from typing import Dict, List, Any

from curl_cffi import requests as cffi_requests


def format_price(price_int: int) -> str:
    """将价格整数格式化为元（东方财富价格单位为厘）"""
    if not isinstance(price_int, (int, float)):
        return '-'
    return f"{price_int / 100:.2f}"


def format_percent(percent_float: float) -> str:
    """格式化百分比（东方财富涨跌幅单位为0.1%）"""
    if not isinstance(percent_float, (int, float)):
        return '-'
    return f"{percent_float / 100:.2f}"


def format_amount(amount_float: float) -> str:
    """格式化金额为亿元"""
    if not isinstance(amount_float, (int, float)):
        return '-'
    return f"{amount_float / 100000000:.2f}"


def format_volume(volume_int: int) -> str:
    """格式化成交量为万手"""
    if not isinstance(volume_int, (int, float)):
        return '-'
    return f"{volume_int / 10000:.2f}"


FIELD_MAPPING = {
    'f12': ('股票代码', lambda x: x),
    'f13': ('市场类型', lambda x: '深圳' if x == 0 else '上海' if x == 1 else str(x)),
    'f14': ('股票名称', lambda x: x),
    'f2': ('当前价', lambda x: x),
    'f3': ('涨跌幅(%)', lambda x: x),
    'f4': ('涨跌额', lambda x: x),
    'f5': ('成交量(万手)', lambda x: x),
    'f6': ('成交额(亿元)', lambda x: x),
    'f7': ('振幅', lambda x: x),
    'f8': ('换手率(%)', lambda x: x),
    'f9': ('市盈率', lambda x: x),
    'f10': ('量比', lambda x: x),

    'f15': ('最高', lambda x: x),
    'f16': ('最低', lambda x: x),
    'f17': ('开盘', lambda x: x),
    'f18': ('昨收', lambda x: x),

    'f20': ('总市值', lambda x: x),
    'f21': ('流通值', lambda x: x),
    'f23': ('市净率(%)', lambda x: x),
    'f152': ('状态', lambda x: x)
}

# 请求头（与浏览器保持一致）
_HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://quote.eastmoney.com/center/gridlist.html',
    'Sec-Fetch-Dest': 'script',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
}

_URL = "https://push2.eastmoney.com/webguest/api/qt/clist/get"

# 默认筛选条件（全部A股板块）
_DEFAULT_FS = "m:0+t:6+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2,m:0+t:81+s:262144+f:!2"

# 各板块筛选条件
_BOARD_FILTERS = [
    'm:0+t:80+f:!2',                  # 创业板
    'm:1+t:2+f:!2',                   # 沪市A股
    'm:1+t:23+f:!2',                  # 其他
    'm:0+t:81+s:262144+f:!2',         # 科创板
    'm:0+t:6+f:!2',                   # 深市主板（有600条分页限制）
]

# 服务器分页限制：pn*pz <= 600，即单次排序最多只能拿到前600条
_PAGE_LIMIT = 600

# 多排序字段（升降序各取600条，合并去重突破限制）
_MULTI_SORT_FIELDS = ['f3', 'f6', 'f12', 'f8']


def _parse_jsonp(text: str) -> dict:
    """从JSONP响应中解析出JSON字典"""
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
        return {}
    try:
        return json.loads(text[start_idx:end_idx + 1])
    except json.JSONDecodeError:
        return {}


def _structure_stock_list(stock_list: list) -> List[Dict[str, Any]]:
    """将原始字段列表转换为结构化中文字段列表"""
    structured_list = []
    for stock in stock_list:
        if not isinstance(stock, dict):
            continue
        structured_stock = {}
        for raw_field, (chinese_name, formatter) in FIELD_MAPPING.items():
            if raw_field in stock:
                structured_stock[chinese_name] = formatter(stock[raw_field])
            else:
                structured_stock[chinese_name] = '-'
        structured_list.append(structured_stock)
    return structured_list


def get_stock_list(
        pn: int = 1,
        pz: int = 100,
        fid: str = "f3",
        po: int = 1,
        fs: str = _DEFAULT_FS
) -> List[Dict[str, Any]]:
    """
    爬取东方财富A股列表接口（使用curl_cffi模拟Chrome TLS指纹）

    :param pn: 页码（从1开始）
    :param pz: 每页条数（默认100，服务器限制 pn*pz<=600）
    :param fid: 排序字段（f3=涨跌幅）
    :param po: 排序方向（1=降序，0=升序）
    :param fs: 筛选条件（板块分类）
    :return: List[Dict] - 结构化股票数据列表，失败返回空列表
    """
    params = {
        'timil': '1',
        'np': '1',
        'fltt': '1',
        'invt': '2',
        'cb': f'jQuery_{int(time.time() * 1000)}',
        'fs': fs,
        'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f20,f21,f23',
        'fid': fid,
        'pn': str(pn),
        'pz': str(pz),
        'po': str(po),
        'dect': '1',
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'wbp2u': '|0|0|0|web',
        '_': str(int(time.time() * 1000))
    }

    try:
        time.sleep(random.uniform(0.3, 0.8))

        response = cffi_requests.get(
            url=_URL,
            params=params,
            headers=_HEADERS,
            impersonate="chrome",
            timeout=30
        )

        if response.status_code != 200:
            print(f"❌ 请求失败，状态码：{response.status_code}")
            return []

        jsonp_text = response.text.strip()
        if not jsonp_text:
            print("❌ JSONP返回为空，无有效数据")
            return []

        stock_json = _parse_jsonp(jsonp_text)
        if not stock_json:
            print(f"❌ JSONP格式解析失败，原始返回前200字符：{jsonp_text[:200]}")
            return []

        data = stock_json.get('data')
        if not data or not isinstance(data, dict):
            print(f"⚠️ 页码{pn}：无股票数据")
            return []

        stock_list = data.get('diff', []) or []
        if not stock_list:
            print(f"⚠️ 页码{pn}：无股票数据")
            return []

        structured_list = _structure_stock_list(stock_list)
        print(f"✅ 页码{pn}：成功爬取{len(structured_list)}条A股数据")
        return structured_list

    except Exception as e:
        print(f"❌ 爬取出错：{str(e)[:100]}，类型：{type(e).__name__}")
        return []


def _get_board_total(fs: str, page_size: int = 20) -> int:
    """获取板块数据总条数（通过第1页响应的total字段）"""
    params = {
        'timil': '1', 'np': '1', 'fltt': '1', 'invt': '2',
        'cb': f'jQuery_{int(time.time() * 1000)}',
        'fs': fs,
        'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f20,f21,f23',
        'fid': 'f3', 'pn': '1', 'pz': str(page_size), 'po': '1', 'dect': '1',
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b', 'wbp2u': '|0|0|0|web',
        '_': str(int(time.time() * 1000))
    }
    try:
        resp = cffi_requests.get(_URL, params=params, headers=_HEADERS, impersonate="chrome", timeout=30)
        stock_json = _parse_jsonp(resp.text.strip())
        data = stock_json.get('data')
        if data and isinstance(data, dict):
            return data.get('total', 0)
    except Exception:
        pass
    return 0


def _fetch_board_all(fs: str, page_size: int = 20) -> List[Dict[str, Any]]:
    """获取单个板块的全部数据（自动判断是否需要多排序字段突破600条限制）"""
    stocks_map = {}  # code -> stock，用于去重
    total = _get_board_total(fs, page_size)
    print(f"  板块 {fs} 总数据量: {total} 条")

    if total <= _PAGE_LIMIT:
        # 数据量不超过600条：单排序字段顺序翻页即可
        need_multi_sort = False
    else:
        need_multi_sort = True

    sort_fields_to_use = _MULTI_SORT_FIELDS if need_multi_sort else ['f3']

    for fid in sort_fields_to_use:
        # 数据量已足够，提前结束
        if len(stocks_map) >= total > 0:
            break
        for po in (1, 0):  # 降序、升序
            if len(stocks_map) >= total > 0:
                break
            page_index = 1
            while True:
                page_stocks = get_stock_list(pn=page_index, pz=page_size, fid=fid, po=po, fs=fs)
                if not page_stocks:
                    break
                for stock in page_stocks:
                    code = stock.get('股票代码')
                    if code and code not in stocks_map:
                        stocks_map[code] = stock
                if len(page_stocks) < page_size:
                    break
                page_index += 1

    return list(stocks_map.values())


def get_all_stock_list(page_size: int = 100) -> List[Dict[str, Any]]:
    """
    爬取东方财富全部A股列表数据

    策略：
    1. 分开获取各个板块，避免组合筛选的600条限制
    2. 对受限制的板块（m:0+t:6+f:!2）使用多排序字段×升降序突破600条限制
    3. 全局按股票代码去重

    :param page_size: 每页条数（默认100）
    :return: List[Dict] - 结构化股票数据列表
    """
    all_stocks = []
    seen_codes = set()

    for fs in _BOARD_FILTERS:
        board_stocks = _fetch_board_all(fs, page_size)
        for stock in board_stocks:
            code = stock.get('股票代码')
            if code and code not in seen_codes:
                seen_codes.add(code)
                all_stocks.append(stock)
        print(f"📊 板块 {fs} 完成，新增 {len(board_stocks)} 条，累计 {len(all_stocks)} 条")

    print(f"🎉 全部板块爬取完成，共获取 {len(all_stocks)} 条股票数据")
    return all_stocks


if __name__ == "__main__":
    stocks = get_all_stock_list(page_size=100)
    print(f"\n📈 共爬取到 {len(stocks)} 条A股数据")
    if stocks:
        print("\n📋 第一条数据详情：")
        for key, value in stocks[0].items():
            print(f"{key}：{value}")
