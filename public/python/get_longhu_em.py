import requests
import time
import json
import random
from typing import Dict, List, Any, Optional
import ssl

# 忽略SSL证书警告（适配macOS/Python3.13，避免请求报错）
ssl._create_default_https_context = ssl._create_unverified_context
requests.packages.urllib3.disable_warnings()

# 新增：随机UA池（防风控，模拟不同浏览器）
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Edge/144.0.0.0 Safari/537.36"
]

def get_eastmoney_daily_billboard(
    start_date: str = "2026-02-25",  # 开始日期（格式YYYY-MM-DD）
    end_date: str = "2026-02-25",    # 结束日期（格式YYYY-MM-DD）
    page_number: int = 1,            # 页码（从1开始）
    page_size: int = 500,             # 每页条数
    sort_columns: str = "SECURITY_CODE,TRADE_DATE",  # 排序列
    sort_types: str = "1,-1"         # 排序类型（1升序，-1降序）
) -> List[Dict[str, Any]]:
    """
    爬取东方财富龙虎榜详情数据（RPT_DAILYBILLBOARD_DETAILSNEW）
    :return: 结构化龙虎榜数据列表，失败/无数据返回空列表
    """
    # 接口基础地址
    url = "https://datacenter-web.eastmoney.com/api/data/v1/get"

    # 动态生成JSONP的cb参数（避免固定值被风控识别）
    cb_prefix = f"jQuery{random.randint(1000000000000000000, 9999999999999999999)}"
    cb_suffix = str(int(time.time() * 1000))
    cb_param = f"{cb_prefix}_{cb_suffix}"

    # 拼接日期筛选条件（与curl一致的filter格式）
    filter_cond = f"(TRADE_DATE<='{end_date}')(TRADE_DATE>='{start_date}')"

    # ✅ 1:1复刻curl请求参数
    params = {
        'callback': cb_param,
        'sortColumns': sort_columns,
        'sortTypes': sort_types,
        'pageSize': str(page_size),
        'pageNumber': str(page_number),
        'reportName': 'RPT_DAILYBILLBOARD_DETAILSNEW',
        'columns': 'SECURITY_CODE,SECUCODE,SECURITY_NAME_ABBR,TRADE_DATE,EXPLAIN,CLOSE_PRICE,CHANGE_RATE,BILLBOARD_NET_AMT,BILLBOARD_BUY_AMT,BILLBOARD_SELL_AMT,BILLBOARD_DEAL_AMT,ACCUM_AMOUNT,DEAL_NET_RATIO,DEAL_AMOUNT_RATIO,TURNOVERRATE,FREE_MARKET_CAP,EXPLANATION,D1_CLOSE_ADJCHRATE,D2_CLOSE_ADJCHRATE,D5_CLOSE_ADJCHRATE,D10_CLOSE_ADJCHRATE,SECURITY_TYPE_CODE',
        'source': 'WEB',
        'client': 'WEB',
        'filter': filter_cond,
        '_': str(int(time.time() * 1000))  # 动态时间戳，防缓存/风控
    }

    # ✅ 1:1复刻curl请求头（新增随机UA）
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        'Connection': 'keep-alive',
        'Referer': 'https://data.eastmoney.com/stock/tradedetail.html',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': random.choice(USER_AGENTS),  # 随机选择UA
        'sec-ch-ua': '"Not(A:Brand";v="8", "Chromium";v="144", "Google Chrome";v="144"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'Host': 'datacenter-web.eastmoney.com'  # 补充Host，增强请求真实性
    }

    # ✅ 1:1复刻curl的Cookies（风控核心）
    cookies = {
        'qgqp_b_id': 'dad4df7ea17c871c09b5242823ffebcd',
        'fullscreengg': '1',
        'fullscreengg2': '1',
        'st_nvi': 'joLj4La65T-7FxIweyM_26d2f',
        'st_si': '23228037692728',
        'nid18': '0e655375199c15d554682723df091ba3',
        'nid18_create_time': '1765096792246',
        'gviem': 'taSB8QvzaYHiU51DKlEpU8cfb',
        'gviem_create_time': '1765096792247',
        'wsc_checkuser_ok': '1',
        'websitepoptg_api_time': '1772006411322',
        'p_origin': 'https%3A%2F%2Fai.eastmoney.com',
        'mtp': '1',
        'ct': 'yS36vnm7FdSt55DOVms-57LS605l0HZucnHdptC10hQ09R71i8NiXWfWrSEQZmL2t_zm1gM0ROr50-uwnLM4mzwsKZntY-_wNqXngugslY9zDPHPCz85PkvuV6ECwbokCHKHcYxkiIZbMn9ls9AccN3F_csMGwf8Aq7coQk7eq4',
        'ut': 'FobyicMgeV52Ad4fCxim_LW4v1o2A2hzFfrNTakB-gOMqG6FSfwghPF3ILPHWkBAYZtBr_a2Xpc8UKHTKTvdwxuq4O5aQ4GbBCVF25bwfbIY3iUke0NCNczjzjbmbh5v00JKuBwefxH-jmtKtQVjJDXJiUeSsPo0YraIzVubgt0PNEMXoBXbhgBVEVjaYKicjApaCDdVFGpFl9YMG0PCFlj9PuyY4f56nE-Ifr1X25CS7CpHl-N9sRBk82w_3-Opt4RX6Qr1PxQ',
        'pi': '6621037720065408%3Bn6621037720065408%3B%E8%82%A1%E5%8F%8B8683V0223F%3BYzWzZUkujoTB%2ByYch%2Ft4MT1z%2FF0ceEAu5cALNTzt9Y%2Be4HPrWczL7CXfQGoeXeBf%2FEGnlrSwiRKFBomsxNAfcDu4GBIlAfkwBswDITKNzfR%2BzZ3onEPtssvwvcx1l1jZ9wP1Ms4qIYsbQ2u3ZDXo06SyoC22dX7k6zW0%2FUABBaGdW0vq5jJ8FhVPaqB4iHZ2fyxXVgg9%3BRs6ugwTn2nG14DI%2FsScPmDcplYIWfeCXKKNDFb%2FYwHvJ%2BOGCq5JgbIFv8xAXJoTTKSnZP%2Bq2SmXwrSHc5No9vgpo2einx3IInLzlgYkh1ssSbX6zafvEyN725JpD7kcDO38Q7eBx5Yx%2BgQtQg37r3XMHdGC1qQ%3D%3D',
        'uidal': '6621037720065408%e8%82%a1%e5%8f%8b8683V0223F',
        'sid': '',
        'vtpst': '|',
        'st_asi': 'delete',
        'JSESSIONID': 'C559F7FF65B923315EBFA85CC0479AC4',
        'st_pvi': '06542231346970',
        'st_sp': '2025-11-18%2000%3A29%3A07',
        'st_inirUrl': 'https%3A%2F%2Fquote.eastmoney.com%2Fcenter%2Fhszs.html',
        'st_sn': '2592',
        'st_psi': '20260225164848743-113300302015-4049348995'
    }

    try:
        # 防风控延时（1.5-3秒随机，模拟真人操作）
        time.sleep(random.uniform(1.5, 3))

        # 关闭长连接，解决远程连接中断问题
        session = requests.Session()
        session.keep_alive = False

        # 发送请求（30秒超时，关闭SSL验证）
        response = session.get(
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            verify=False,
            timeout=30
        )
        session.close()  # 立即关闭连接，避免风控

        # 状态码校验
        if response.status_code == 200:
            jsonp_text = response.text.strip()
            if not jsonp_text:
                print(f"❌ 日期[{start_date}至{end_date}]：龙虎榜接口返回为空，无有效数据")
                return []

            # ✅ 核心：解析JSONP格式（精准字符串截取，避开正则兼容问题）
            start_idx = jsonp_text.find('{')  # 定位第一个左大括号
            end_idx = jsonp_text.rfind('}')   # 定位最后一个右大括号
            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                print(f"❌ 日期[{start_date}至{end_date}]：JSONP格式解析失败，原始返回前500字符：{jsonp_text[:500]}")
                return []

            # 提取纯JSON字符串并解析
            json_str = jsonp_text[start_idx:end_idx+1]
            try:
                billboard_json = json.loads(json_str)
            except json.JSONDecodeError:
                print(f"❌ 日期[{start_date}至{end_date}]：JSON解析失败，截取内容：{json_str[:500]}")
                return []

            # ✅ 多层级空值防护+接口状态校验（避免KeyError/类型错误）
            if not isinstance(billboard_json, dict) or not billboard_json.get('success'):
                err_msg = billboard_json.get('message', '接口返回异常，未获取到数据')
                print(f"❌ 日期[{start_date}至{end_date}]：{err_msg}")
                return []

            # 提取核心龙虎榜数据
            result = billboard_json.get('result', {})
            billboard_list = result.get('data', []) if isinstance(result, dict) else []
            if not isinstance(billboard_list, list) or len(billboard_list) == 0:
                print(f"⚠️ 日期[{start_date}至{end_date}] 页码[{page_number}]：无龙虎榜数据返回")
                return []

            # ✅ 结构化字段映射（核心：抽象字段→易读中文，单位标准化）
            field_mapping = {
                'SECURITY_CODE': '股票代码',
                'SECUCODE': '证券代码(市场后缀)',
                'SECURITY_NAME_ABBR': '股票名称',
                'TRADE_DATE': '交易日期',
                'EXPLAIN': '龙虎榜解读',
                'CLOSE_PRICE': '收盘价(元)',
                'CHANGE_RATE': '涨跌幅(%)',
                'BILLBOARD_NET_AMT': '龙虎榜净买额(元)',
                'BILLBOARD_BUY_AMT': '龙虎榜买入额(元)',
                'BILLBOARD_SELL_AMT': '龙虎榜卖出额(元)',
                'BILLBOARD_DEAL_AMT': '龙虎榜成交额(元)',
                'ACCUM_AMOUNT': '市场总成交额(元)',
                'DEAL_NET_RATIO': '净买额占总成交比(%)',
                'DEAL_AMOUNT_RATIO': '龙虎榜成交额占总成交比(%)',
                'TURNOVERRATE': '换手率(%)',
                'FREE_MARKET_CAP': '流通市值(元)',
                'EXPLANATION': '上榜原因',
                'D1_CLOSE_ADJCHRATE': '1日后涨跌幅(%)',
                'D2_CLOSE_ADJCHRATE': '2日后涨跌幅(%)',
                'D5_CLOSE_ADJCHRATE': '5日后涨跌幅(%)',
                'D10_CLOSE_ADJCHRATE': '10日后涨跌幅(%)',
                'SECURITY_TYPE_CODE': '证券类型代码'
            }

            # 转换为易读的结构化数据，做数值类型校验
            structured_data = []
            for billboard in billboard_list:
                if not isinstance(billboard, dict):
                    continue
                billboard_dict = {}
                for raw_field, cn_field in field_mapping.items():
                    value = billboard.get(raw_field, '-')
                    # 数值类型转换（失败则保留原值，避免程序崩溃）
                    try:
                        if value != '-' and isinstance(value, (int, float)):
                            billboard_dict[cn_field] = round(float(value), 4)
                        else:
                            billboard_dict[cn_field] = value
                    except:
                        billboard_dict[cn_field] = value
                # 保留原始字段，方便扩展
                billboard_dict['原始字段'] = billboard
                structured_data.append(billboard_dict)

            # 打印爬取结果日志
            total_count = result.get('count', 0)
            total_pages = result.get('pages', 0)
            print(f"✅ 日期[{start_date}至{end_date}] 页码[{page_number}]：成功爬取{len(structured_data)}条龙虎榜数据 | 总数据{total_count}条 | 总页数{total_pages}页")
            return structured_data

        else:
            print(f"❌ 日期[{start_date}至{end_date}]：请求失败，状态码：{response.status_code}，响应前200字符：{response.text[:200]}")
            return []

    # ✅ 全覆盖异常处理（确保程序不崩溃，所有场景返回空列表）
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 日期[{start_date}至{end_date}]：连接被风控拦截：{str(e)[:100]}")
        print("💡 解决方案：1. 切换手机热点 2. 5分钟后重试 3. 更新Cookies")
        return []
    except requests.exceptions.Timeout:
        print(f"❌ 日期[{start_date}至{end_date}]：请求超时（30秒未收到响应）")
        return []
    except Exception as e:
        print(f"❌ 日期[{start_date}至{end_date}]：爬取出错：{str(e)[:100]}，错误类型：{type(e).__name__}")
        return []

# ========== 调用示例（与你的curl参数完全一致，直接运行） ==========
if __name__ == "__main__":
    # 爬取2026-02-25单日的龙虎榜数据（默认第1页，每页50条）
    billboard_data = get_eastmoney_daily_billboard(
        start_date="2026-03-05",
        end_date="2026-03-05",
        page_number=1,
        page_size=500
    )

    # 友好展示数据，避免索引越界报错
    if billboard_data:
        print(f"\n📈 共爬取到{len(billboard_data)}条龙虎榜数据")
        print("\n📋 第一条龙虎榜详情：")
        first_billboard = billboard_data[0]
        for key, value in first_billboard.items():
            if key != '原始字段':  # 跳过原始字段，只展示易读内容
                print(f"{key}：{value}")

        # 【可选】将数据保存为CSV文件，方便后续分析
        import pandas as pd
        df = pd.DataFrame(billboard_data)
        df.to_csv("20260225龙虎榜详情数据.csv", index=False, encoding="utf-8-sig")
        print("\n💾 数据已保存为 20260225龙虎榜详情数据.csv")
    else:
        print("\n⚠️ 未爬取到任何龙虎榜数据")