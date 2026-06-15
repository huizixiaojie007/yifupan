import subprocess
import time
import json
from typing import List, Dict, Any


def get_capital_flow_list(
        page_size: int = 50,
        page_num: int = 1,
        sort_field: str = 'f62',
        sort_order: int = 1
) -> List[Dict[str, Any]]:
    """获取东方财富资金流向排名列表（通过系统curl请求，绕过TLS指纹检测）

    Args:
        page_size: 每页数量，默认50
        page_num: 页码，默认1
        sort_field: 排序字段，默认f62(主力净流入)
        sort_order: 排序方向，1倒序，0正序

    Returns:
        list: 资金流向数据列表，每项包含股票代码、名称、价格、资金流向等
    """
    # URL中fs参数的!必须编码为%21，与浏览器行为一致
    url = (
        f"https://push2.eastmoney.com/api/qt/clist/get"
        f"?cb=jQuery37102720261681126638_{int(time.time() * 1000)}"
        f"&fid={sort_field}"
        f"&po={sort_order}"
        f"&pz={page_size}"
        f"&pn={page_num}"
        f"&np=1"
        f"&fltt=2"
        f"&invt=2"
        f"&ut=8dec03ba335b81bf4ebdf7b29ec27d15"
        f"&fs=m%3A0%2Bt%3A6%2Bf%3A%212%2Cm%3A0%2Bt%3A13%2Bf%3A%212%2Cm%3A0%2Bt%3A80%2Bf%3A%212%2Cm%3A1%2Bt%3A2%2Bf%3A%212%2Cm%3A1%2Bt%3A23%2Bf%3A%212%2Cm%3A0%2Bt%3A7%2Bf%3A%212%2Cm%3A1%2Bt%3A3%2Bf%3A%212"
        f"&fields=f12%2Cf14%2Cf2%2Cf3%2Cf62%2Cf184%2Cf66%2Cf69%2Cf72%2Cf75%2Cf78%2Cf81%2Cf84%2Cf87%2Cf124%2Cf13"
    )

    curl_cmd = [
        'curl', '-sS',
        '-H', 'Accept: */*',
        '-H', 'Accept-Language: en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        '-H', 'Referer: https://data.eastmoney.com/zjlx/detail.html',
        '-H', 'Sec-Fetch-Dest: script',
        '-H', 'Sec-Fetch-Mode: no-cors',
        '-H', 'Sec-Fetch-Site: same-site',
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36',
        '-H', 'sec-ch-ua: "Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
        '-H', 'sec-ch-ua-mobile: ?0',
        '-H', 'sec-ch-ua-platform: "macOS"',
        url
    ]

    try:
        result = subprocess.run(
            curl_cmd,
            capture_output=True,
            text=True,
            timeout=15
        )

        if result.returncode != 0:
            print(f"❌ curl执行失败，返回码: {result.returncode}，错误: {result.stderr[:200]}")
            return []

        jsonp_text = result.stdout.strip()
        if not jsonp_text:
            print(f"❌ curl返回为空，stderr: {result.stderr[:200]}")
            return []

        start_idx = jsonp_text.find('{')
        end_idx = jsonp_text.rfind('}')
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            print(f"❌ JSONP格式解析失败，原始返回前500字符：{jsonp_text[:500]}")
            return []

        json_str = jsonp_text[start_idx:end_idx + 1]
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            print(f"❌ JSON解析失败，截取内容：{json_str[:500]}")
            return []

        if not isinstance(data, dict):
            print("❌ 解析结果非字典类型，无数据")
            return []

        if data.get('rc') != 0:
            print(f"❌ 资金流向接口返回异常: {data.get('msg', '无')}")
            return []

        result_data = data.get('data', {})
        diff = result_data.get('diff', []) if isinstance(result_data, dict) else []
        if not isinstance(diff, list) or not diff:
            print(f"❌ 资金流向接口无数据返回")
            return []

        field_mapping = {
            'f12': '股票代码',
            'f14': '股票名称',
            'f2': '最新价',
            'f3': '涨跌幅',
            'f62': '主力净流入',
            'f184': '主力净流入占比',
            'f66': '超大单净流入',
            'f69': '超大单净流入占比',
            'f72': '大单净流入',
            'f75': '大单净流入占比',
            'f78': '中单净流入',
            'f81': '中单净流入占比',
            'f84': '小单净流入',
            'f87': '小单净流入占比',
            'f13': '市场编号'
        }

        stock_list = []
        for item in diff:
            if not isinstance(item, dict):
                continue
            stock = {}
            for field_code, field_name in field_mapping.items():
                stock[field_name] = item.get(field_code, '-')
            stock_list.append(stock)

        total = result_data.get('total', 0)
        print(f"✅ 资金流向数据获取成功，共{total}条，当前第{page_num}页返回{len(stock_list)}条")
        return stock_list

    except subprocess.TimeoutExpired:
        print(f"❌ curl请求超时（15秒未响应）")
        return []
    except FileNotFoundError:
        print(f"❌ 未找到curl命令，请确保系统已安装curl")
        return []
    except Exception as e:
        print(f"⚠️  资金流向请求失败: {str(e)[:100]}，类型：{type(e).__name__}")
        return []


if __name__ == '__main__':
    print("=" * 50)
    print("测试资金流向排名（前10）")
    print("=" * 50)
    flow_list = get_capital_flow_list(page_size=10)
    for i, stock in enumerate(flow_list, 1):
        print(f"\n{i}. {stock['股票名称']}({stock['股票代码']})")
        print(f"  最新价: {stock['最新价']}  涨跌幅: {stock['涨跌幅']}%")
        print(f"  主力净流入: {stock['主力净流入']}  占比: {stock['主力净流入占比']}%")
        print(f"  超大单净流入: {stock['超大单净流入']}  大单净流入: {stock['大单净流入']}")
