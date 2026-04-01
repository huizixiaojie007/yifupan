import requests
import time
import json
from typing import Optional, List, Dict

# 忽略SSL证书警告
requests.packages.urllib3.disable_warnings()


def get_eastmoney_zt_pool(
        date: str = "20260113",
        page_index: int = 0,
        page_size: int = 200,
        sort: str = "fbt:asc"
) -> Optional[List[Dict]]:
    """
    爬取东方财富涨停池接口数据（修复code=None异常）
    :param date: 日期（格式：YYYYMMDD，如20260113）
    :param page_index: 页码（从0开始）
    :param page_size: 每页条数（默认170）
    :param sort: 排序规则（默认fbt:asc）
    :return: List[Dict] - 涨停池数据列表，失败返回None
    """
    # ========== 1. 接口基础配置 ==========
    url = "https://push2ex.eastmoney.com/getTopicZTPool"

    # 请求参数（从你的curl复刻，支持自定义传参）
    params = {
        'cb': 'callbackdata528449',
        'ut': '7eea3edcaed734bea9cbfc24409ed989',
        'dpt': 'wz.ztzt',
        'Pageindex': str(page_index),
        'pagesize': str(page_size),
        'sort': sort,
        'date': date,
        '_': str(int(time.time() * 1000))  # 动态时间戳，防缓存
    }

    # 请求头（和你的curl完全一致）
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        'Connection': 'keep-alive',
        'Referer': 'https://quote.eastmoney.com/ztb/detail',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    }

    # Cookies（和你的curl完全一致）
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
        'st_sn': '1553',
        'st_psi': '20260113152246153-113200304537-6431889874'
    }

    try:
        # 防风控：加0.5秒延时
        time.sleep(0.5)

        # 发送GET请求（该接口为GET请求）
        response = requests.get(
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            verify=False,
            timeout=15
        )

        # ========== 2. 响应处理：精准解析JSONP ==========
        if response.status_code == 200:
            jsonp_text = response.text.strip()

            # 精准截取大括号内的JSON内容
            start_idx = jsonp_text.find('{')
            end_idx = jsonp_text.rfind('}')

            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                print(f"❌ JSONP格式解析失败，原始返回：{jsonp_text[:500]}")
                return None

            # 截取并解析JSON
            json_str = jsonp_text[start_idx:end_idx + 1]
            zt_json = json.loads(json_str)

            # ========== 核心修复：打印完整返回JSON，定位真实结构 ==========
            # print(f"📝 接口完整返回JSON：{json.dumps(zt_json, ensure_ascii=False, indent=2)}")

            # 调整状态判断：不依赖code字段，直接判断data是否存在
            zt_data = zt_json.get('data', {}).get('pool', [])
            if not zt_data:
                print(f"⚠️ 日期{date}页码{page_index}：无涨停池数据返回（可能是Cookies过期/日期无数据/参数错误）")
                return []

            print(f"✅ 日期{date}页码{page_index}：爬取到{len(zt_data)}条涨停池数据", zt_data)
            return zt_data

        else:
            print(f"❌ 请求失败，状态码：{response.status_code}，响应内容：{response.text[:500]}")
            return None

    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（15秒未响应）")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败，错误：{str(e)}，截取的JSON字符串：{json_str[:500]}")
        return None
    except Exception as e:
        print(f"❌ 爬取出错，错误信息：{str(e)}")
        return None


# ========== 调用测试 ==========
if __name__ == '__main__':
    # 爬取20260113第0页（默认170条）
    zt_data = get_eastmoney_zt_pool(date="20260113", page_index=0)
    if zt_data:
        print(f"\n📈 共爬取到{len(zt_data)}条涨停池数据")
        # 打印第一条数据示例
        if zt_data:
            print("\n📋 第一条数据详情：")
            for key, value in zt_data[0].items():
                print(f"{key}：{value}")