import random

import requests
import time
import json
from typing import Dict, List, Any
import ssl

# 忽略SSL证书警告（适配macOS/Python3.13）
ssl._create_default_https_context = ssl._create_unverified_context
requests.packages.urllib3.disable_warnings()


def get_eastmoney_special_stock_list(
        pn: int = 1,  # 页码（从1开始）
        pz: int = 200,  # 每页条数（默认20）
        fid: str = "f3",  # 排序字段（f3=涨跌幅）
        po: int = 1,  # 排序方向（1=升序，-1=降序）
        fs: str = "m:90+t:2+f:!50"  # 核心筛选条件（m:90+t:3对应特定分类）m:90+t:2+f:!50板块分类 。m:90+t:3+f:!50 概念分类
) -> List[Dict[str, Any]]:
    """
    爬取东方财富特定分类股票列表接口（JSONP格式）
    :param pn: 页码
    :param pz: 每页条数
    :param fid: 排序字段（f3=涨跌幅，f2=最新价，f5=成交量）
    :param po: 排序方向（1=升序，-1=降序）
    :param fs: 筛选条件（m:90+t:3+f:!50 对应指定分类）
    :return: List[Dict] - 结构化股票数据列表，失败返回空列表
    """
    # ========== 1. 接口基础配置（1:1复刻你的curl） ==========
    url = "https://push2.eastmoney.com/api/qt/clist/get"

    # 请求参数（还原所有curl参数，处理转义字符\u0021=!）
    params = {
        'np': '1',
        'fltt': '1',
        'invt': '2',
        'cb': 'jQuery37102720261681126638_1770787293365',
        'fs': fs,
        'fields': 'f12,f13,f14,f1,f2,f4,f3,f152,f20,f8,f104,f105,f128,f140,f141,f207,f208,f209,f136,f222',
        'fid': fid,
        'pn': str(pn),
        'pz': str(pz),
        'po': str(po),
        'dect': '1',
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'wbp2u': '|0|0|0|web',
        '_': str(int(time.time() * 1000))  # 动态时间戳，防缓存/风控
    }

    # 请求头（完全复刻你的curl）
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
        'Host': 'push2.eastmoney.com'  # 增强请求真实性
    }

    # Cookies（完全复刻你的curl，保留所有有效字段）
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
        'st_sn': '2278',
        'st_psi': '20260211131442606-113200301328-3017968455'
    }

    try:
        # 防风控延时（关键，避免IP封禁）
        time.sleep(random.uniform(1, 3))

        # ========== 2. 发送请求 ==========
        # 关闭长连接，解决系统内部异常和连接中断问题
        session = requests.Session()
        session.keep_alive = False  # 核心优化：禁用HTTP长连接

        # 发送请求（30秒超时，关闭SSL验证）
        response = session.get(
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            verify=False,
            timeout=30
        )
        session.close()  # 立即关闭连接，减少风控检测

        if response.status_code == 200:
            jsonp_text = response.text.strip()
            if not jsonp_text:
                print("❌ JSONP返回为空，无有效数据")
                return []

            # ========== 3. 核心：解析JSONP格式（精准截取） ==========
            # 定位JSON边界，避开正则兼容问题
            start_idx = jsonp_text.find('{')
            end_idx = jsonp_text.rfind('}')
            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                print(f"❌ JSONP格式解析失败，原始返回前500字符：{jsonp_text[:500]}")
                return []

            # 提取纯JSON并解析
            json_str = jsonp_text[start_idx:end_idx + 1]
            try:
                stock_json = json.loads(json_str)
            except json.JSONDecodeError:
                print(f"❌ JSON解析失败，截取内容：{json_str[:500]}")
                return []

            # ========== 4. 多层级空值防护（避免KeyError） ==========
            if not isinstance(stock_json, dict):
                print("❌ 解析结果非字典类型，无数据")
                return []

            # 提取核心股票列表（diff字段）
            data = stock_json.get('data', {})
            stock_list = data.get('diff', []) if isinstance(data, dict) else []
            if not isinstance(stock_list, list):
                print("❌ 股票列表非列表类型，返回空")
                return []

            if not stock_list:
                print(f"⚠️ 页码{pn}：无股票数据（页码超限/分类无数据）")
                return []

            # ========== 5. 结构化字段映射（新增字段全覆盖） ==========
            # 完整字段含义映射（包含本次新增的f20/f104等）
            field_mapping = {
                'f12': '股票代码',
                'f14': '股票名称',
                'f2': '最新价',
                'f3': '涨跌幅',
                'f4': '涨跌额',
                'f13': '类型',
                'f20': '总市值',
                'f8': '换手率',
                'f104': '上涨家数',
                'f105': '下跌家数',
                'f128': '领涨股票',
                'f136': '领涨股涨幅',
                'f140': '领涨股代码',
                'f207': '领跌股票',
                'f208': '领跌股代码',
                'f222': '领跌股跌幅',
            }

            # 转换为易读的结构化数据
            structured_list = []
            for stock in stock_list:
                if not isinstance(stock, dict):
                    continue

                structured_stock = {}
                # 映射中文字段
                for raw_field, desc_field in field_mapping.items():
                    structured_stock[desc_field] = stock.get(raw_field, '-')
                # 保留原始数据（方便扩展）
                structured_stock['原始字段'] = stock
                structured_list.append(structured_stock)

            print(f"✅ 页码{pn}：成功爬取{len(structured_list)}条股票数据")
            return structured_list

        else:
            print(f"❌ 请求失败，状态码：{response.status_code}，响应：{response.text[:200]}")
            return []

    # ========== 全覆盖异常处理（确保不崩溃） ==========
    except requests.exceptions.ConnectionError as e:
        print(f"❌ 连接被风控拦截：{str(e)[:100]}")
        print("💡 解决方案：1. 切换手机热点 2. 5分钟后重试 3. 更新Cookies")
        return []
    except requests.exceptions.Timeout:
        print(f"❌ 请求超时（30秒未响应）")
        return []
    except Exception as e:
        print(f"❌ 爬取出错：{str(e)[:100]}，类型：{type(e).__name__}")
        return []


# ========== 调用示例（与你的curl参数完全一致） ==========
if __name__ == "__main__":
    # 爬取m:90+t:3分类第1页，每页20条，按涨跌幅升序排列
    stock_data = get_eastmoney_special_stock_list()
