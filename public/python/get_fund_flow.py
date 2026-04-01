import requests
import re
import json
import pandas as pd
from datetime import datetime

#个股资金实时流向
def get_eastmoney_capital_flow(secid="0.000001"):
    """
    获取东方财富个股资金流向K线数据
    :param secid: 股票secid，格式：沪市=1.60XXXX，深市=0.00XXXX/0.30XXXX
    :param save_to_excel: 是否保存为Excel文件（默认False）
    :return: 格式化后的资金流向DataFrame
    """
    # 1. 构造请求参数和请求头
    url = "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
    # 随机生成cb回调名称（模拟浏览器请求，可固定）
    cb_name = f"jQuery11230{int(datetime.now().timestamp() * 1000)}_{int(datetime.now().timestamp() * 1000)}"
    params = {
        "cb": cb_name,
        "lmt": 0,
        "klt": 1,
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65",
        "ut": "b2884a393a59ad64002292a3e90d46a5",
        "secid": secid,
        "_": int(datetime.now().timestamp() * 1000)
    }

    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6",
        "Connection": "keep-alive",
        # 注意：Cookie可能过期，若请求失败请替换为自己浏览器的Cookie
        "Cookie": "qgqp_b_id=dad4df7ea17c871c09b5242823ffebcd; fullscreengg=1; fullscreengg2=1; st_nvi=joLj4La65T-7FxIweyM_26d2f; st_si=23228037692728; wsc_checkuser_ok=1; nid18=0e655375199c15d554682723df091ba3; nid18_create_time=1765096792246; gviem=taSB8QvzaYHiU51DKlEpU8cfb; gviem_create_time=1765096792247; st_pvi=06542231346970; st_sp=2025-11-18%2000%3A29%3A07; st_inirUrl=https%3A%2F%2Fquote.eastmoney.com%2Fcenter%2Fhszs.html; st_sn=613; st_psi=20251223200250741-113300300815-1608115223; st_asi=delete",
        "Referer": f"https://data.eastmoney.com/zjlx/{secid.split('.')[1]}.html",
        "Sec-Fetch-Dest": "script",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "sec-ch-ua": "\"Google Chrome\";v=\"143\", \"Chromium\";v=\"143\", \"Not A(Brand\";v=\"24\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"macOS\""
    }

    try:
        # 2. 发送GET请求
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()  # 抛出HTTP请求异常
        print("请求成功，开始解析数据...")

        # 步骤1：剥离jQuery回调，提取JSON字符串
        # 正则匹配：去掉开头的"jQueryXXX(" 和结尾的");"
        jsonp_pattern = re.compile(r'^[^(]+\((.*)\);$')
        match = jsonp_pattern.match(response.text)
        if not match:
            raise ValueError("未匹配到JSONP格式数据")

        # 步骤2：将JSON字符串转为Python字典
        json_str = match.group(1)
        data_dict = json.loads(json_str)

        # 步骤3：逐层提取klines（容错处理，避免键不存在报错）
        if "data" not in data_dict:
            raise KeyError("数据中缺少'data'键")
        if "klines" not in data_dict["data"]:
            raise KeyError("data中缺少'klines'键")

        klines_list = data_dict["data"]["klines"]
        print(f"成功提取klines数据，共 {len(klines_list)} 条记录")

        # 分割每条记录并转为DataFrame
        klines_rows = [line.split(",") for line in klines_list]
        # print("klines_rows:::", klines_rows)
        return klines_rows


    except re.error as e:
        print(f"正则匹配失败：{e}")
        return None, None
    except json.JSONDecodeError as e:
        print(f"JSON解析失败：{e}")
        return None, None
    except KeyError as e:
        print(f"字段缺失：{e}")
        return None, None
    except Exception as e:
        print(f"提取klines失败：{e}")
        return None, None


# ------------------- 调用示例 -------------------
if __name__ == "__main__":
    # 配置参数：secid格式说明
    # 沪市股票：1.60XXXX（如贵州茅台=1.600519）
    # 深市股票：0.00XXXX/0.30XXXX（如平安银行=0.000001，宁德时代=0.300750）
    target_secid = "0.000001"  # 平安银行（深市）
    # target_secid = "1.600519"  # 贵州茅台（沪市）

    # 获取数据
    capital_flow_df = get_eastmoney_capital_flow(
        secid=target_secid
    )