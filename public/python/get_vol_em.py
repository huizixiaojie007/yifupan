import requests
import time
import json
from typing import Optional, Dict, List

# 忽略SSL证书警告
requests.packages.urllib3.disable_warnings()


def get_eastmoney_sse_stock_detail(stock_code: str) -> Optional[Dict]:
    """
    爬取东方财富SSE股票详情接口（流式返回text/event-stream）
    :param stock_code: 股票代码（如002465/300063/600000）
    :return: Dict - 结构化的股票详情数据，失败返回None
    """
    # ========== 1. 自动识别市场，生成secid（东方财富secid规则） ==========
    market_map = {
        '0': ['300', '002', '000', '001'],  # 深市（创业板/中小板/主板）
        '1': ['60', '68'],  # 沪市（主板/科创板）
        '8': ['8']  # 北交所
    }
    secid = None
    stock_prefix = stock_code[:3] if len(stock_code) >= 3 else stock_code[:1]
    for market_code, prefixes in market_map.items():
        if any(stock_code.startswith(p) for p in prefixes):
            secid = f"{market_code}.{stock_code}"
            break
    if not secid:
        print(f"❌ 股票代码{stock_code}格式错误，无法识别市场")
        return None

    # ========== 2. 接口配置（1:1复刻你的curl） ==========
    url = "https://7.push2.eastmoney.com/api/qt/stock/details/sse"
    params = {
        'fields1': 'f1,f2,f3,f4',
        'fields2': 'f51,f52,f53,f54,f55',
        'mpi': '2000',
        'ut': 'bd1d9ddb04089700cf9c27f6f7426281',
        'fltt': '2',
        'pos': '-0',
        'secid': secid,
        'wbp2u': '|0|0|0|web'
    }

    headers = {
        'Accept': 'text/event-stream',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Origin': 'https://quote.eastmoney.com',
        'Referer': f'https://quote.eastmoney.com/f1.html?newcode={secid}',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    }

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
        'st_sn': '1645',
        'st_psi': '20260114162954551-113200304537-0482977319'
    }

    try:
        # 防风控延时
        time.sleep(0.5)

        # ========== 3. 处理SSE流式返回（核心！区别于普通JSON） ==========
        # 发送GET请求，开启流式响应
        response = requests.get(
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            verify=False,
            timeout=20,
            stream=True  # 关键：开启流式读取，适配text/event-stream
        )

        if response.status_code == 200:
            sse_data = {}
            # 迭代读取流式响应的每一行
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    # 过滤空行，提取data: 开头的行（SSE格式核心）
                    if line.startswith('data: '):
                        # 去掉前缀"data: "，获取纯JSON字符串
                        json_str = line.lstrip('data: ').strip()
                        # 跳过空数据（如data: []）
                        if json_str in ['[]', '{}', '']:
                            continue
                        try:
                            # 解析JSON数据
                            stock_detail = json.loads(json_str)
                            sse_data = stock_detail
                            # SSE可能返回多行，取最后一条有效数据即可
                            break  # 如需所有流式数据，可注释break，用列表收集
                        except json.JSONDecodeError as e:
                            print(f"❌ 股票{stock_code}：JSON解析失败，行内容：{json_str[:200]}，错误：{e}")
                            continue

            if not sse_data:
                print(f"⚠️ 股票{stock_code}：SSE流式返回无有效数据")
                return {}

            # ========== 4. 结构化字段映射（易读） ==========
            # 字段含义参考东方财富接口文档
            field_mapping = {
                # fields1 基础字段
                'f1': '未知字段1',
                'f2': '最新价',
                'f3': '涨跌幅(%)',
                'f4': '涨跌额',
                # fields2 详情字段
                'f51': '时间戳/交易时间',
                'f52': '成交价格',
                'f53': '成交量',
                'f54': '成交额',
                'f55': '买卖方向（1买/2卖）'
            }

            # 提取核心数据（兼容不同返回结构）
            structured_data = {'secid': secid, '股票代码': stock_code}
            # 解析fields1数据
            fields1_data = sse_data.get('data', {}).get('fields1', [])
            fields2_data = sse_data.get('data', {}).get('fields2', [])
            # 映射fields1
            for idx, (field_code, field_name) in enumerate(field_mapping.items()):
                if field_code.startswith('f1') and idx < len(fields1_data):
                    structured_data[field_name] = fields1_data[idx]
            # 映射fields2
            fields2_codes = ['f51', 'f52', 'f53', 'f54', 'f55']
            for idx, field_code in enumerate(fields2_codes):
                field_name = field_mapping.get(field_code, field_code)
                if idx < len(fields2_data):
                    structured_data[field_name] = fields2_data[idx]

            # 保留原始完整数据
            structured_data['原始完整数据'] = sse_data

            print(f"✅ 股票{stock_code}（secid:{secid}）：SSE详情数据爬取成功")
            return structured_data

        else:
            print(f"❌ 股票{stock_code}：请求失败，状态码{response.status_code}，响应内容：{response.text[:500]}")
            return None

    except requests.exceptions.Timeout:
        print(f"❌ 股票{stock_code}：请求超时（20秒未响应）")
        return None
    except requests.exceptions.ChunkedEncodingError:
        print(f"❌ 股票{stock_code}：SSE流式响应中断（风控/连接关闭）")
        return None
    except Exception as e:
        print(f"❌ 股票{stock_code}：爬取出错，错误信息：{str(e)}")
        return None


# ========== 调用示例 ==========
if __name__ == '__main__':
    # 测试002465（你的示例代码）
    stock_code = "002465"
    stock_detail = get_eastmoney_sse_stock_detail(stock_code)
    if stock_detail:
        print("\n📈 股票SSE详情数据：")
        for key, value in stock_detail.items():
            if key != '原始完整数据':
                print(f"{key}：{value}")

        # 可选：打印原始完整数据，查看所有字段
        # print("\n📋 原始完整数据：")
        # print(json.dumps(stock_detail['原始完整数据'], ensure_ascii=False, indent=2))