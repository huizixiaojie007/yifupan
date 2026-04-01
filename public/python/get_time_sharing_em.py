import requests
import time
import json
from typing import Optional, Dict, List, Any
import ssl

# 忽略SSL证书警告（适配macOS/Python3.13）
ssl._create_default_https_context = ssl._create_unverified_context
requests.packages.urllib3.disable_warnings()


def get_eastmoney_stock_trend_sse(
        symbol: str,
        ndays: int = 1,  # 获取天数（默认1天）
        mpi: int = 1000,  # 每页条数（默认1000）
        iscr: int = 0,  # 复权开关（0=不复权）
        iscca: int = 0  # 盘口类型（0=默认）
) -> List[Any]:  # 统一返回列表，避免None导致的报错
    """
    爬取东方财富SSE股票趋势接口（text/event-stream流式返回）
    :param stock_code: 股票代码（如000048/601212/300063）
    :param ndays: 获取天数（默认1天）
    :param mpi: 每页返回条数（默认1000）
    :param iscr: 复权开关（0=不复权，1=前复权，2=后复权）
    :param iscca: 盘口类型（0=默认）
    :return: List - 股票趋势数据列表（空列表=无数据/失败）
    """
    # ========== 1. 自动生成secid + 修复Referer拼接（核心报错点1） ==========
    secid = ""
    market_prefix = "sz"  # 默认深市
    if symbol.startswith(("00", "30", "20")):
        secid = f"0.{symbol}"  # 深市股票
        market_prefix = "sz"
    elif symbol.startswith(("60", "68", "90")):
        secid = f"1.{symbol}"  # 沪市股票
        market_prefix = "sh"  # 沪市用sh，修复Referer错误
    elif symbol.startswith(("92", "93")):
        secid = f"0.{symbol}"  # 沪市股票
        market_prefix = "bj"  # 沪市用sh，修复Referer错误
    else:
        print(f"❌ 股票代码[{symbol}]格式错误，仅支持A股6位数字代码")
        return []  # 返回空列表，避免None报错

    # ========== 2. 接口基础配置 ==========
    url = "https://82.push2.eastmoney.com/api/qt/stock/trends2/sse"

    params = {
        'fields1': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f17',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58',
        'mpi': str(mpi),
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'secid': secid,
        'ndays': str(ndays),
        'iscr': str(iscr),
        'iscca': str(iscca),
        'wbp2u': '1849325530509956|0|1|0|web',
        '_': str(int(time.time() * 1000))  # 动态时间戳，防缓存
    }

    headers = {
        'Accept': 'text/event-stream',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Origin': 'https://quote.eastmoney.com',
        'Referer': f'https://quote.eastmoney.com/concept/{market_prefix}{symbol}.html',  # 修复沪市Referer
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'Host': '82.push2.eastmoney.com'
    }

    # ========== 3. 优化Cookies（减少空值依赖） ==========
    cookies = {
        'qgqp_b_id': 'dad4df7ea17c871c09b5242823ffebcd',
        'st_si': '23228037692728',
        'st_pvi': '06542231346970',
        'st_sp': '2025-11-18%2000%3A29%3A07',
        'nid18': '0e655375199c15d554682723df091ba3',
        # 空字段不影响基础请求，移除易过期的字段避免报错
    }

    try:
        time.sleep(1.5)

        # ========== 4. 核心：处理SSE流式返回 + 完善异常防护 ==========
        response = requests.get(
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            verify=False,
            timeout=30,
            stream=True
        )

        trend_data_list = []
        if response.status_code == 200:
            # 迭代读取流式响应，增加异常防护
            for line in response.iter_lines(decode_unicode=True, chunk_size=1024):
                if not line:
                    continue  # 跳过空行，避免处理空字符串报错

                # 提取data:开头的行
                if line.startswith('data: '):
                    json_str = line.lstrip('data: ').strip()
                    if json_str in ['[]', '{}', '', 'null']:
                        continue

                    # 包裹JSON解析，避免解析失败报错（核心报错点2）
                    try:
                        trend_json = json.loads(json_str)
                    except json.JSONDecodeError:
                        continue  # 解析失败跳过，不中断程序

                    # 多层级空值防护，避免KeyError（核心报错点3）
                    data = trend_json.get('data', {}) if isinstance(trend_json, dict) else {}
                    trends = data.get('trends', []) if isinstance(data, dict) else []
                    if isinstance(trends, list):
                        trend_data_list = trends
                    break  # 取第一条有效数据，避免无限循环

            # ========== 5. 解析trends字符串为易读字典（核心优化） ==========
            # 东方财富trends返回的是逗号分隔的字符串，解析成字段映射
            parsed_data = []
            # 趋势字段含义（东方财富官方映射）
            trend_fields = [
                "时间", "开盘", "收盘", "最高", "最低","成交量", "成交额", "均价"
            ]
            for item in trend_data_list:
                if isinstance(item, str):
                    parts = item.split(',')
                    # 长度匹配，避免索引越界报错
                    item_dict = {
                        trend_fields[i]: parts[i] if i < len(parts) else ""
                        for i in range(min(len(trend_fields), len(parts)))
                    }
                    parsed_data.append(item_dict)
                else:
                    parsed_data.append(item)  # 非字符串直接保留

            # print('parsed_data:::', parsed_data)
            return parsed_data

        else:
            print(f"❌ 请求失败，状态码：{response.status_code}")
            return []  # 返回空列表，避免None报错

    # ========== 6. 全覆盖异常处理 + 统一返回空列表 ==========
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接被拒绝（风控拦截）：{str(e)[:100]}")
        print("💡 解决方案：1. 切换网络（手机热点） 2. 5分钟后重试")
        return []
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（30秒未响应）")
        return []
    except requests.exceptions.ChunkedEncodingError:
        print(f"❌ SSE流式响应中断")
        return []
    except Exception as e:
        print(f"❌ 爬取出错：{str(e)[:100]}")
        return []


# ========== 调用示例（修复遍历逻辑，避免报错） ==========
if __name__ == "__main__":
    # 爬取000048 1天的趋势数据
    trend_data = get_eastmoney_stock_trend_sse( symbol="000048" )