import requests
import time
import json
from typing import Optional, List, Dict

# 忽略SSL证书警告
requests.packages.urllib3.disable_warnings()


def get_eastmoney_stock_ann(
        begin_time: str = "2026-01-22",
        end_time: str = "2026-01-22",
        page_index: int = 1,
        page_size: int = 100,
        sr: int = -1,  # 排序：-1降序/1升序
        ann_type: str = "SHA,CYB,SZA,BJA,INV"  # 公告类型：沪A/创业板/深A/北A/调研
) -> Optional[List[Dict]]:
    """
    爬取东方财富股票公告接口数据
    :param begin_time: 开始日期（格式：YYYY-MM-DD）
    :param end_time: 结束日期（格式：YYYY-MM-DD）
    :param page_index: 页码（从1开始）
    :param page_size: 每页条数（默认50）
    :param sr: 排序方式（-1降序，1升序）
    :param ann_type: 公告类型（SHA=沪A, CYB=创业板, SZA=深A, BJA=北A, INV=调研）
    :return: List[Dict] - 公告数据列表，失败返回None
    """
    # ========== 1. 接口基础配置 ==========
    url = "https://np-anotice-stock.eastmoney.com/api/security/ann"

    # 请求参数（1:1复刻你的curl）
    params = {
        'cb': 'jQuery112304983637817518193_1769006701301',
        'sr': str(sr),
        'page_size': str(page_size),
        'page_index': str(page_index),
        'ann_type': ann_type,
        'client_source': 'web',
        'f_node': '0',
        's_node': '0',
        'begin_time': begin_time,
        'end_time': end_time,
        '_': str(int(time.time() * 1000))  # 动态时间戳，防缓存
    }

    # 请求头（完全复刻你的curl）
    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        'Connection': 'keep-alive',
        'Referer': 'https://data.eastmoney.com/notices/hsa/7.html',
        'Sec-Fetch-Dest': 'script',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    }

    # Cookies（完全复刻你的curl）
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
        'st_sn': '2077',
        'st_psi': '20260121224501597-113300301011-7416351782',
        'st_asi': 'delete'
    }

    try:
        # 防风控延时
        time.sleep(0.5)

        # 发送GET请求
        response = requests.get(
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            verify=False,
            timeout=20
        )

        # ========== 2. 核心：精准解析JSONP格式 ==========
        if response.status_code == 200:
            jsonp_text = response.text.strip()

            # 精准截取大括号内的JSON内容（避开正则坑）
            start_idx = jsonp_text.find('{')
            end_idx = jsonp_text.rfind('}')

            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                print(f"❌ JSONP格式解析失败，原始返回前500字符：{jsonp_text[:500]}")
                return None

            # 截取并解析JSON
            json_str = jsonp_text[start_idx:end_idx + 1]
            ann_json = json.loads(json_str)
            # 检查接口返回状态
            total_count = ann_json.get('total_count', 0)
            ann_list = ann_json.get('data', {}).get('list', [])

            if not ann_list:
                print(f"⚠️ {begin_time}至{end_time} 页码{page_index}：无公告数据返回（总条数：{total_count}）")
                return []
            
            # 处理公告列表，生成指定格式数据
            result = []
            stock_data_map = {}
            
            for ann in ann_list:
                try:
                    # 提取所需字段
                    art_code = ann.get('art_code', '')
                    codes = ann.get('codes', [])
                    title = ann.get('title', '')
                    
                    if not codes:
                        continue
                    
                    # 获取第一个股票代码信息
                    first_code = codes[0]
                    short_name = first_code.get('short_name', '')
                    stock_code = first_code.get('stock_code', '')
                    
                    if not stock_code:
                        continue
                    
                    # 创建公告数据
                    notice_data = {'code': art_code, 'title': title}
                    
                    # 检查是否已存在该股票的数据
                    if stock_code in stock_data_map:
                        # 合并数据
                        stock_data_map[stock_code]['data'].append(notice_data)
                    else:
                        # 创建新的股票数据
                        stock_data_map[stock_code] = {
                            'gp_name': short_name,
                            'gp_no': stock_code,
                            'data': [notice_data]
                        }
                except Exception as e:
                    print(f"❌ 处理单条公告失败：{str(e)}")
                    continue
            
            # 转换为列表格式
            result = list(stock_data_map.values())
            
            print(f"✅ 处理完成，共生成 {len(result)} 条股票公告数据", result)
            return result

        else:
            print(f"❌ 请求失败，状态码：{response.status_code}，响应内容：{response.text[:500]}")
            return None

    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（20秒未响应）")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析失败，错误：{str(e)}，截取的JSON字符串：{json_str[:500]}")
        return None
    except Exception as e:
        print(f"❌ 爬取出错，错误信息：{str(e)}")
        return None


# ========== 调用示例 ==========
if __name__ == '__main__':
    # 示例1：爬取2026-01-22第1页（50条）公告
    ann_data = get_eastmoney_stock_ann(
        begin_time="2026-01-24",
        end_time="2026-01-24",
        page_index=1,
        page_size=100
    )

    if ann_data:
        print(f"\n📢 共爬取到{len(ann_data)}条公告数据")
        # 打印第一条公告示例
        if ann_data:
            print("\n📋 第一条公告详情：")
            for key, value in ann_data[0].items():
                if key != '原始字段':
                    print(f"{key}：{value}")

        # 示例2：批量爬取多页（如需）
        # all_ann_data = []
        # for page in range(1, 3):  # 爬取第1、2页
        #     data = get_eastmoney_stock_ann(page_index=page)
        #     if data:
        #         all_ann_data.extend(data)
        # print(f"\n📊 批量爬取总公告数：{len(all_ann_data)}")