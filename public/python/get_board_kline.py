import requests
import time
import json
from typing import Dict, List, Any, Optional
import ssl

# 忽略SSL证书警告（适配macOS/Python3.13，避免请求报错）
ssl._create_default_https_context = ssl._create_unverified_context
requests.packages.urllib3.disable_warnings()

def get_board_kline(
        secid: str = "90.BK1128",  # 核心入参：板块/股票secid（如90.BK1128、0.000048）
        klt: int = 101,  # K线类型（101=日线，102=周线，103=月线，5=5分钟）
        fqt: int = 1,  # 复权类型（1=前复权，0=不复权，2=后复权）
        beg: str = "0",  # 开始时间（0=全部，格式YYYYMMDD）
        end: str = "20500101",  # 结束时间
        lmt: int = 120  # 返回数据上限
) -> List[Dict[str, Any]]:
    """
    爬取东方财富股票/板块K线数据接口（JSONP格式）
    :return: 结构化K线数据列表，失败/无数据返回空列表
    """
    # 接口基础地址
    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    # ✅ 1:1复刻curl请求参数
    params = {
        'cb': 'jQuery351043419617332312976_1771485877541',
        'secid': secid,
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'fields1': 'f1,f2,f3,f4,f5,f6',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
        'klt': str(klt),
        'fqt': str(fqt),
        'beg': beg,
        'end': end,
        'lmt': str(lmt),
        '_': str(int(time.time() * 1000))  # 动态时间戳，防风控/缓存
    }

    # ✅ 1:1复刻curl请求头
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        'Connection': 'keep-alive',
        'Referer': f'https://quote.eastmoney.com/bk/{secid}.html',  # 动态拼接Referer
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'Host': 'push2his.eastmoney.com'  # 补充Host，增强请求真实性
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
        'st_pvi': '06542231346970',
        'st_sp': '2025-11-18%2000%3A29%3A07',
        'st_inirUrl': 'https%3A%2F%2Fquote.eastmoney.com%2Fcenter%2Fhszs.html',
        'st_sn': '2376',
        'st_psi': '20260213150816794-113200301328-3161311798',
        'st_asi': 'delete'
    }

    try:
        # 防风控延时（关键，避免IP被高频封禁）
        time.sleep(1.5)

        # 发送请求（关闭SSL验证，适配HTTPS）
        response = requests.get(
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            verify=False,
            timeout=30
        )

        # 状态码校验
        if response.status_code == 200:
            jsonp_text = response.text.strip()
            if not jsonp_text:
                print(f"❌ secid[{secid}]：K线接口返回为空，无有效数据")
                return []

            # ✅ 核心：解析JSONP格式（精准字符串截取，避开正则兼容问题）
            start_idx = jsonp_text.find('{')  # 定位第一个左大括号
            end_idx = jsonp_text.rfind('}')  # 定位最后一个右大括号
            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                print(f"❌ secid[{secid}]：JSONP格式解析失败，原始返回前500字符：{jsonp_text[:500]}")
                return []

            # 提取纯JSON字符串并解析
            json_str = jsonp_text[start_idx:end_idx + 1]
            try:
                kline_json = json.loads(json_str)
            except json.JSONDecodeError:
                print(f"❌ secid[{secid}]：JSON解析失败，截取的内容：{json_str[:500]}")
                return []

            # ✅ 多层级空值防护（避免KeyError/类型错误）
            if not isinstance(kline_json, dict):
                print(f"❌ secid[{secid}]：解析结果非字典类型，无有效数据")
                return []

            # 校验接口返回状态
            if kline_json.get('rc') != 0:
                print(f"❌ secid[{secid}]：接口返回异常，msg={kline_json.get('msg', '未知错误')}")
                return []

            # 提取K线核心数据
            data = kline_json.get('data', {})
            kline_list = data.get('klines', []) if isinstance(data, dict) else []
            if not isinstance(kline_list, list) or len(kline_list) == 0:
                print(f"⚠️ secid[{secid}]：无K线数据返回（secid无效/非交易时间）")
                return []

            # ✅ 结构化K线数据映射（核心：将字符串数组转为易读字典）
            # K线字段含义映射（fields2：f51-f61）
            kline_fields = [
                "日期", "开盘价", "收盘价", "最高价", "最低价",
                "成交量", "成交额",  "振幅(%)", "涨跌幅(%)","涨跌额", "换手率(%)"
            ]

            structured_kline = []
            for kline_str in kline_list:
                if not isinstance(kline_str, str) or len(kline_str) == 0:
                    continue

                # 拆分逗号分隔的K线字符串
                kline_parts = kline_str.split(',')
                kline_dict = {}

                # 映射字段（长度匹配，避免索引越界）
                for i in range(min(len(kline_fields), len(kline_parts))):
                    # 数值类型转换（字符串→数字，失败则保留原字符串）
                    try:
                        value = float(kline_parts[i]) if kline_fields[i] != "日期" else kline_parts[i]
                    except ValueError:
                        value = kline_parts[i]
                    kline_dict[kline_fields[i]] = value

                structured_kline.append(kline_dict)

            print(f"✅ secid[{secid}]：成功爬取{len(structured_kline)}条{_get_klt_desc(klt)}K线数据")
            return structured_kline

        else:
            print(f"❌ secid[{secid}]：请求失败，状态码：{response.status_code}，响应前200字符：{response.text[:200]}")
            return []

    # ✅ 全覆盖异常处理（确保程序不崩溃，所有场景返回空列表）
    except requests.exceptions.ConnectionError as e:
        print(f"❌ secid[{secid}]：连接被风控拦截：{str(e)[:100]}")
        print("💡 解决方案：1. 切换手机热点 2. 5分钟后重试 3. 更新Cookies")
        return []
    except requests.exceptions.Timeout:
        print(f"❌ secid[{secid}]：请求超时（30秒未收到响应）")
        return []
    except Exception as e:
        print(f"❌ secid[{secid}]：爬取出错：{str(e)[:100]}，错误类型：{type(e).__name__}")
        return []


def _get_klt_desc(klt: int) -> str:
    """辅助函数：返回K线类型描述"""
    klt_map = {
        5: "5分钟", 15: "15分钟", 30: "30分钟", 60: "60分钟",
        101: "日线", 102: "周线", 103: "月线", 104: "季线", 105: "年线"
    }
    return klt_map.get(klt, f"未知({klt})")


# ========== 调用示例（与你的curl参数完全一致，直接运行） ==========
if __name__ == "__main__":
    # 爬取90.BK1128板块日线K线数据（你的原始需求）
    board_kline = get_board_kline(
        secid="90.BK0729"
    )
