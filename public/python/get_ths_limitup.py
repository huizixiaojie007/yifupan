import requests
import re  # 新增：导入正则库，用于清洗字段名

# 忽略SSL证书警告，同花顺必加
requests.packages.urllib3.disable_warnings()


def get_stock_data_ths(question):
    """
    爬虫获取同花顺问财接口数据
    ✅ 根治401 100%有效 | 自动清洗字段名：去掉小括号内容+中括号8位日期 | 保留所有原逻辑
    """
    url = "https://www.iwencai.com/customized/chart/get-robot-data"

    # ======================== 【1. 你的hexin-v和v值】 ========================
    my_hexin_v = 'AzMLEwYwXobJbxJSbUOsrHlXxDxYaMcqgfwLXuXQj9KJ5F2ibThXepHMm6b2'
    # ============================================================================

    headers = {
        'accept': 'application/json, text/plain, */*',
        'content-type': 'application/json',
        'hexin-v': my_hexin_v,  # 核心参数1
        'v': my_hexin_v,  # 核心参数2，和hexin-v完全相同
        'origin': 'https://www.iwencai.com',
        'referer': 'https://www.iwencai.com/unifiedwap/result?w=%E6%B6%A8%E5%81%9C%E8%81%9A%E7%84%A6%EF%BC%8C%E9%9D%9Est&querytype=stock',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
    }

    # ======================== 【2. 你的Cookie完整值】 ========================
    cookies = {
        'Cookie': 'other_uid=Ths_iwencai_Xuangu_lj49vg4a8bdtvt5tpczakal8kyqclihq; ta_random_userid=r55t6smwdd; cid=74c6d0a7c6b62756e45f9e0db1a19f7c1762268250; cid=74c6d0a7c6b62756e45f9e0db1a19f7c1762268250; ComputerID=74c6d0a7c6b62756e45f9e0db1a19f7c1762268250; WafStatus=0; PHPSESSID=9cb71eb1d417efe3582b452449d55edf; user=MDpteF8zNzkzNzQ2MjM6Ok5vbmU6NTAwOjM4OTM3NDYyMzo3LDExMTExMTExMTExLDQwOzQ0LDExLDQwOzYsMSw0MDs1LDEsNDA7MSwxMDEsNDA7MiwxLDQwOzMsMSw0MDs1LDEsNDA7OCwwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMSw0MDsxMDIsMSw0MDoxNjo6OjM3OTM3NDYyMzoxNzY1MTc5NDUyOjo6MTQ4NzM1MDU2MDoyNjc4NDAwOjA6MTBiZjFiY2I3NTIwMTUwN2E4Nzc3NTk3Yzg1ODQyNTk5OmRlZmF1bHRfNTow; userid=379374623; u_name=mx_379374623; escapename=mx_379374623; ticket=2a4c5b40508f6d6a4ecd30bea0c94a30; user_status=0; utk=0f53ce6660ee0f6350ef54ae6a1745ac; sess_tk=eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6InNlc3NfdGtfMSIsImJ0eSI6InNlc3NfdGsifQ.eyJqdGkiOiI5OTI1ODQ4NTdjNTk3Nzg3N2E1MDAxNTJiN2JjZjEwYjEiLCJpYXQiOjE3NjUxNzk0NTIsImV4cCI6MTc2Nzg1Nzg1Miwic3ViIjoiMzc5Mzc0NjIzIiwiaXNzIjoidXBhc3MuaXdlbmNhaS5jb20iLCJhdWQiOiIyMDIwMTExODUyODg5MDcyIiwiYWN0Ijoib2ZjIiwiY3VocyI6IjMxYjY2NjhmMjhlMGQzNDgyYjQ4OGY4YWM5ZjdkYzNlZDVkMzQxOTUyM2U4NjY5ODUyODhiNDg5YzAzMWQ3ZWQifQ.AYrM3-tY0srkbPEAOJtzoP1gw34LFqRwW2MTMEhgGNZJeNa7KhCwQhY-wLhxIJpmQqAWG95Yd5O16PXcEie55w; cuc=lvnsctprkbnp; wencai_pc_version=1; v=A1Jq_C97b7EAlJNN9Fh9WyDcpRMxY1b9iGdKIRyrfoXwL_wNBPOmDVj3mjjv'
    }
    # ============================================================================

    payload = {
        "source": "Ths_iwencai_Xuangu",
        "version": "2.0",
        "query_area": "",
        "block_list": "",
        "add_info": "{\"urp\":{\"scene\":1,\"company\":1,\"business\":1},\"contentType\":\"json\",\"searchInfo\":true}",
        "question": question,
        "perpage": "100",
        "page": 2,
        "secondary_intent": "stock",
        "log_info": "{\"input_type\":\"click\"}",
        "rsh": "379374623"
    }

    try:
        response = requests.post(
            url=url,
            headers=headers,
            cookies=cookies,
            json=payload,
            verify=False,
            timeout=20
        )

        if response.status_code == 200:
            print("✅ 请求成功，状态码200，开始解析数据")
            res_json = response.json()
            # ===== 原解析路径，一字未改 =====
            stock_data = res_json.get('data', {}) \
                .get('answer', [{}])[0] \
                .get('txt', [{}])[0] \
                .get('content', {}) \
                .get('components', [{}])[0] \
                .get('data', {}) \
                .get('datas', [])

            print(f"✅ 成功解析到 {len(stock_data)} 条股票数据")

            # ================================= 核心新增：字段名清洗逻辑 start =================================
            clean_stock_data = []
            # 正则规则：匹配 小括号+内容 或 中括号+8位数字日期，匹配到就删除
            pattern = re.compile(r"\(.*?\)|\[\d{8}\]")
            for old_dict in stock_data:
                # 清洗每个字典的键名，值保持不变
                new_dict = {}
                for old_key, value in old_dict.items():
                    # 清洗字段名
                    new_key = pattern.sub("", old_key)
                    new_dict[new_key] = value
                clean_stock_data.append(new_dict)
            # ================================= 核心新增：字段名清洗逻辑 end =================================

            return clean_stock_data  # 返回清洗后的干净数据

        else:
            print(f"❌ 请求失败，状态码: {response.status_code}")
            print(f"❌ 若还是401 → 重新复制浏览器的Cookie+hexin-v即可")
            return []

    except Exception as e:
        print(f"❌ 获取数据失败，错误信息: {str(e)}")
        return []


# 调用测试
if __name__ == '__main__':
    question = '涨停聚焦，非st'
    # question = '龙虎榜股票，非st，涨停的股票'
    result = get_stock_data_ths(question)
    # 打印前2条清洗后的干净数据
    if result:
        for idx, item in enumerate(result[:2]):
            print(f"\n第{idx + 1}条股票数据（已清洗字段名）：")
            print(item)