import random
import time
import json
from typing import Dict, List, Any, Optional

from curl_cffi import requests as cffi_requests


# 字段映射：英文字段 -> (中文名, 格式化函数)
FIELD_MAPPING = {
    'MXID': ('明细ID', lambda x: x),
    'H_COMNAME': ('受让方名称', lambda x: x if x else '-'),
    'G_GOMNAME': ('出让方名称', lambda x: x if x else '-'),
    'S_COMNAME': ('上市公司名称', lambda x: x if x else '-'),
    'SCODE': ('股票代码', lambda x: x),
    'SNAME': ('股票名称', lambda x: x if x else '-'),
    'ZRBL': ('转让比例(%)', lambda x: round(x / 100, 2) if isinstance(x, (int, float)) else x),
    'OBJTYPE': ('标的类型', lambda x: x if x else '-'),
    'JYJE': ('交易金额(元)', lambda x: x if x else '-'),
    'JD': ('进度', lambda x: x if x else '-'),
    'ZRFS': ('转让方式', lambda x: x if x else '-'),
    'SCGGRQ': ('首次公告日期', lambda x: x.split(' ')[0] if isinstance(x, str) and ' ' in x else x),
    'ANNOUNDATE': ('公告日期', lambda x: x.split(' ')[0] if isinstance(x, str) and ' ' in x else x),
    'BZNAME': ('标准名称', lambda x: x if x else '-'),
    'TJEBZH': ('特别提示', lambda x: x if x else '-'),
    'MKT': ('市场', lambda x: '沪市' if x == 'sh' else '深市' if x == 'sz' else (x or '-')),
    'REORGANIZECODE': ('重组代码', lambda x: x if x else '-'),
}

# 请求头
_HEADERS = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://data.eastmoney.com/bgcz/',
    'Sec-Fetch-Dest': 'script',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'same-site',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
}

_URL = "https://datacenter-web.eastmoney.com/api/data/v1/get"

# 固定 token（从页面抓取的）
_TOKEN = "894050c76af8597a853f5b408b759f5d"

# 默认排序：首次公告日期降序
_DEFAULT_SORT_COLUMN = "SCGGRQ"
_DEFAULT_SORT_TYPE = -1  # -1=降序, 1=升序


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


def _structure_row(row: dict) -> Dict[str, Any]:
    """将原始行数据转换为结构化中文字段"""
    structured = {}
    for raw_field, (chinese_name, formatter) in FIELD_MAPPING.items():
        if raw_field in row:
            structured[chinese_name] = formatter(row[raw_field])
        else:
            structured[chinese_name] = '-'
    return structured


def get_bgcz_list(
    page_number: int = 1,
    page_size: int = 50,
    sort_column: str = _DEFAULT_SORT_COLUMN,
    sort_type: int = _DEFAULT_SORT_TYPE
) -> List[Dict[str, Any]]:
    """
    爬取东方财富并购重组明细列表

    :param page_number: 页码（从1开始）
    :param page_size: 每页条数（默认50）
    :param sort_column: 排序字段（默认SCGGRQ=首次公告日期）
    :param sort_type: 排序方向（-1=降序，1=升序）
    :return: List[Dict] - 结构化并购重组明细列表，失败返回空列表
    """
    params = {
        'callback': f'jQuery_{int(time.time() * 1000)}_{random.randint(1000000000, 9999999999)}',
        'sortColumns': sort_column,
        'sortTypes': str(sort_type),
        'pageSize': str(page_size),
        'pageNumber': str(page_number),
        'columns': 'ALL',
        'source': 'WEB',
        'token': _TOKEN,
        'reportName': 'RPTA_WEB_BGCZMX',
    }

    try:
        time.sleep(random.uniform(0.2, 0.6))

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

        if not stock_json.get('success'):
            msg = stock_json.get('message', '未知错误')
            print(f"❌ 接口返回失败：{msg}")
            return []

        result = stock_json.get('result')
        if not result or not isinstance(result, dict):
            print(f"⚠️ 页码{page_number}：无数据")
            return []

        data_list = result.get('data', []) or []
        if not data_list:
            print(f"⚠️ 页码{page_number}：无数据")
            return []

        structured_list = [_structure_row(row) for row in data_list]
        print(f"✅ 页码{page_number}：成功爬取{len(structured_list)}条并购重组明细")
        return structured_list

    except Exception as e:
        print(f"❌ 爬取出错：{str(e)[:120]}，类型：{type(e).__name__}")
        return []


def get_bgcz_total_count() -> int:
    """获取并购重组明细总条数"""
    result = get_bgcz_list(page_number=1, page_size=1)
    if not result:
        return 0
    # 需要实际从响应的count字段获取，这里调用一次快速接口
    params = {
        'callback': f'jQuery_{int(time.time() * 1000)}',
        'sortColumns': _DEFAULT_SORT_COLUMN,
        'sortTypes': str(_DEFAULT_SORT_TYPE),
        'pageSize': '1',
        'pageNumber': '1',
        'columns': 'ALL',
        'source': 'WEB',
        'token': _TOKEN,
        'reportName': 'RPTA_WEB_BGCZMX',
    }
    try:
        resp = cffi_requests.get(_URL, params=params, headers=_HEADERS, impersonate="chrome", timeout=30)
        data = _parse_jsonp(resp.text.strip())
        result = data.get('result')
        if result and isinstance(result, dict):
            return result.get('count', 0)
    except Exception:
        pass
    return 0


def get_all_bgcz_list(
    page_size: int = 50,
    max_pages: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    爬取全部并购重组明细

    :param page_size: 每页条数（默认50）
    :param max_pages: 最大页数（None=爬取全部）
    :return: List[Dict] - 全部结构化数据列表
    """
    all_data = []
    total_count = get_bgcz_total_count()
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0

    print(f"📊 并购重组明细总数据量: {total_count} 条，共 {total_pages} 页")

    if max_pages and max_pages < total_pages:
        total_pages = max_pages
        print(f"⚠️  限制仅爬取前 {total_pages} 页")

    page_index = 1
    while page_index <= total_pages:
        page_data = get_bgcz_list(page_number=page_index, page_size=page_size)
        if not page_data:
            print(f"⚠️  页码{page_index}：无数据，提前结束")
            break
        all_data.extend(page_data)
        page_index += 1

    print(f"🎉 爬取完成，共获取 {len(all_data)} 条并购重组明细")
    return all_data


if __name__ == "__main__":
    # 测试：获取前3页
    print("=== 测试并购重组明细爬取（前3页，每页5条）===")
    test_data = get_all_bgcz_list(page_size=5, max_pages=3)

    if test_data:
        print(f"\n📈 共爬取到 {len(test_data)} 条数据")
        print("\n📋 第1条数据详情：")
        for key, value in test_data[0].items():
            print(f"  {key}：{value}")
