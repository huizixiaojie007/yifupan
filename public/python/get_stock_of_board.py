import requests
import time
import json
from typing import Dict, List, Any
import ssl

# 忽略SSL证书警告（适配macOS/Python3.13）
ssl._create_default_https_context = ssl._create_unverified_context
requests.packages.urllib3.disable_warnings()

def get_stock_of_board_em(
    block_code: str = "bk0519",  # 板块代码（核心入参，支持任意bk开头代码）
    pn: int = 1,                 # 页码（从1开始）
    pz: int = 100,                # 每页条数
    fid: str = "f3",             # 排序字段（f3=涨跌幅）
    po: int = 1                  # 排序方向（1=升序，-1=降序）
) -> List[Dict[str, Any]]:
    """
    爬取东方财富指定板块的股票列表（JSONP格式）
    :param block_code: 板块代码（如bk0519、bk0655等）
    :return: 结构化股票数据列表，失败/无数据返回空列表
    """
    # 接口基础地址
    url = "https://push2.eastmoney.com/api/qt/clist/get"

    # ✅ 动态拼接板块筛选条件（核心：将板块代码作为入参）
    fs = f"b:{block_code}+f:!50"  # 拼接规则：b:板块代码+f:!50

    # ✅ 1:1复刻curl请求参数
    params = {
        'np': '1',
        'fltt': '1',
        'invt': '2',
        'cb': 'jQuery37109478939702391624_1770795414325',
        'fs': fs,                  # 动态传入板块筛选条件
        'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f5,f6,f7,f15,f18,f16,f17,f10,f8,f9,f23',
        'fid': fid,
        'pn': str(pn),
        'pz': str(pz),
        'po': str(po),
        'dect': '1',
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'wbp2u': '|0|0|0|web',
        '_': str(int(time.time() * 1000))  # 动态时间戳，防风控
    }

    # ✅ 1:1复刻curl请求头
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        'Connection': 'keep-alive',
        'Referer': 'https://quote.eastmoney.com/center/gridlist.html',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'Host': 'push2.eastmoney.com'
    }

    # ✅ 1:1复刻curl的Cookies
    cookies = {
        'qgqp_b_id': 'dad4df7ea17c871c09b5242823ffebcd',
        'fullscreengg': '1',
        'fullscreengg2': '1',
        'st_nvi': 'joLj4La65T-7FxIweyM_26d2f',
        'st_si': '23228037692728',
        'wsc_checkuser_ok': '1',
        'nid18': '0e655375199c15d554682723df091ba3',
        'nid18_create_time': '1765096792246',
        'gviem': 'taSB8QvzaYHiU51DKlEpU8cfb',
        'gviem_create_time': '1765096792247',
        'st_asi': 'delete',
        'st_pvi': '06542231346970',
        'st_sp': '2025-11-18%2000%3A29%3A07',
        'st_inirUrl': 'https%3A%2F%2Fquote.eastmoney.com%2Fcenter%2Fhszs.html',
        'st_sn': '2302',
        'st_psi': '20260211153655861-113200301321-6668749254'
    }

    try:
        # 防风控延时
        time.sleep(1.5)

        # 发送请求
        response = requests.get(
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            verify=False,
            timeout=30
        )

        if response.status_code == 200:
            jsonp_text = response.text.strip()
            if not jsonp_text:
                print(f"❌ 板块[{block_code}]：接口返回为空，无有效数据")
                return []

            # ✅ 解析JSONP格式（精准截取）
            start_idx = jsonp_text.find('{')
            end_idx = jsonp_text.rfind('}')
            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                print(f"❌ 板块[{block_code}]：JSONP解析失败，原始返回前500字符：{jsonp_text[:500]}")
                return []

            # 解析纯JSON
            json_str = jsonp_text[start_idx:end_idx+1]
            try:
                stock_json = json.loads(json_str)
            except json.JSONDecodeError:
                print(f"❌ 板块[{block_code}]：JSON解析失败，截取内容：{json_str[:500]}")
                return []

            # ✅ 多层级空值防护（避免KeyError）
            if not isinstance(stock_json, dict):
                print(f"❌ 板块[{block_code}]：解析结果非字典类型")
                return []
            data = stock_json.get('data', {})
            stock_list = data.get('diff', []) if isinstance(data, dict) else []
            if not isinstance(stock_list, list):
                print(f"❌ 板块[{block_code}]：股票列表非数组类型")
                return []
            if not stock_list:
                print(f"⚠️ 板块[{block_code}] 页码[{pn}]：无股票数据（页码超限/板块无数据）")
                return []

            # ✅ 结构化字段映射（易读中文）
            field_mapping = {
                'f12': '股票代码',
                'f14': '股票名称',
                'f2': '最新价',
                'f4': '涨跌额',
                'f3': '涨跌幅',
                'f5': '成交量',
                'f6': '成交额',
                'f7': '振幅',
                'f15': '最高价',
                'f18': '昨收价',
                'f16': '最低价',
                'f17': '今开价',
                'f10': '量比',
                'f8': '换手率',
                'f9': '市盈率',
                'f23': '市净率'
            }

            # 转换为易读数据
            structured_data = []
            for stock in stock_list:
                if not isinstance(stock, dict):
                    continue
                stock_dict = {}
                for raw_field, cn_field in field_mapping.items():
                    stock_dict[cn_field] = stock.get(raw_field, '-')
                stock_dict['原始字段'] = stock
                structured_data.append(stock_dict)

            print(f"✅ 板块[{block_code}] 页码[{pn}]：成功爬取{len(structured_data)}条股票数据")
            return structured_data

        else:
            print(f"❌ 板块[{block_code}]：请求失败，状态码：{response.status_code}，响应前200字符：{response.text[:200]}")
            return []

    # ✅ 全覆盖异常处理
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 板块[{block_code}]：连接被风控拦截：{str(e)[:100]}")
        print("💡 解决方案：1. 切换手机热点 2. 5分钟后重试 3. 更新Cookies")
        return []
    except requests.exceptions.Timeout:
        print(f"❌ 板块[{block_code}]：请求超时（30秒未响应）")
        return []
    except Exception as e:
        print(f"❌ 板块[{block_code}]：爬取出错：{str(e)[:100]}，错误类型：{type(e).__name__}")
        return []

# ========== 调用示例（支持任意板块代码传入） ==========
if __name__ == "__main__":
    # 示例1：爬取bk0519板块（你的原始需求）
    bk0519_data = get_stock_of_board_em(
        block_code="bk0519"  # 传入板块代码
    )
