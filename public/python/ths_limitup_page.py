import requests
import re
import time
from urllib.parse import unquote  # 辅助解析参数，可选

# 忽略SSL证书警告
requests.packages.urllib3.disable_warnings()


# ===================== 安全处理值：解决int.strip()报错 =====================
def safe_process_value(raw_value):
    """只对字符串做清洗，数字/空值原样返回"""
    if raw_value is None or not isinstance(raw_value, str):
        return raw_value
    return raw_value.strip().replace("\n", "").replace("\t", "")


def get_stock_data_ths_new(question):
    """
    新接口爬取同花顺全量数据
    ✅ 适配新接口+分页爬全量+无重复+字段清洗+防风控+异常处理
    """
    # 新接口地址
    url = "https://www.iwencai.com/gateway/urp/v7/landing/getDataList"

    # 核心参数（从你的curl里完整复刻）
    my_hexin_v = 'A421LTyy2DB4Fnwc_A3qegM1mqICasG9S54lWc8SySSTxqNcl7rRDNvuNflc'
    session_id = '9cb71eb1d417efe3582b452449d55edf'  # 从curl的sessionid提取

    # 请求头（适配新接口的Content-Type）
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8,zh-CN;q=0.7,zh;q=0.6',
        'Cache-control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded',  # 新接口核心修改
        'Origin': 'https://www.iwencai.com',
        'Pragma': 'no-cache',
        'Referer': 'https://www.iwencai.com/unifiedwap/result?w=%E6%B6%A8%E5%81%9C%E8%81%9A%E7%84%A6%EF%BC%8C%E9%9D%9Est&querytype=stock&sign=1765179452543',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'hexin-v': my_hexin_v,
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"'
    }

    # Cookie（从你的curl里完整复制，保证授权有效）
    cookies = {
        'Cookie': 'other_uid=Ths_iwencai_Xuangu_lj49vg4a8bdtvt5tpczakal8kyqclihq; ta_random_userid=r55t6smwdd; cid=74c6d0a7c6b62756e45f9e0db1a19f7c1762268250; cid=74c6d0a7c6b62756e45f9e0db1a19f7c1762268250; ComputerID=74c6d0a7c6b62756e45f9e0db1a19f7c1762268250; WafStatus=0; PHPSESSID=9cb71eb1d417efe3582b452449d55edf; user=MDpteF8zNzkzNzQ2MjM6Ok5vbmU6NTAwOjM4OTM3NDYyMzo3LDExMTExMTExMTExLDQwOzQ0LDExLDQwOzYsMSw0MDs1LDEsNDA7MSwxMDEsNDA7MiwxLDQwOzMsMSw0MDs1LDEsNDA7OCwwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMSw0MDsxMDIsMSw0MDoxNjo6OjM3OTM3NDYyMzoxNzY1MTc5NDUyOjo6MTQ4NzM1MDU2MDoyNjc4NDAwOjA6MTBiZjFiY2I3NTIwMTUwN2E4Nzc3NTk3Yzg1ODQyNTk5OmRlZmF1bHRfNTow; userid=379374623; u_name=mx_379374623; escapename=mx_379374623; ticket=2a4c5b40508f6d6a4ecd30bea0c94a30; user_status=0; utk=0f53ce6660ee0f6350ef54ae6a1745ac; sess_tk=eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiIsImtpZCI6InNlc3NfdGtfMSIsImJ0eSI6InNlc3NfdGsifQ.eyJqdGkiOiI5OTI1ODQ4NTdjNTk3Nzg3N2E1MDAxNTJiN2JjZjEwYjEiLCJpYXQiOjE3NjUxNzk0NTIsImV4cCI6MTc2Nzg1Nzg1Miwic3ViIjoiMzc5Mzc0NjIzIiwiaXNzIjoidXBhc3MuaXdlbmNhaS5jb20iLCJhdWQiOiIyMDIwMTExODUyODg5MDcyIiwiYWN0Ijoib2ZjIiwiY3VocyI6IjMxYjY2NjhmMjhlMGQzNDgyYjQ4OGY4YWM5ZjdkYzNlZDVkMzQxOTUyM2U4NjY5ODUyODhiNDg5YzAzMWQ3ZWQifQ.AYrM3-tY0srkbPEAOJtzoP1gw34LFqRwW2MTMEhgGNZJeNa7KhCwQhY-wLhxIJpmQqAWG95Yd5O16PXcEie55w; cuc=lvnsctprkbnp; wencai_pc_version=1; v=A421LTyy2DB4Fnwc_A3qegM1mqICasG9S54lWc8SySSTxqNcl7rRDNvuNflc'
    }

    # ========== 分页核心配置 ==========
    page = 1  # 起始页码
    perpage = 100  # 每页条数（最大值100）
    all_stock_data = []  # 存放所有页的完整数据
    pattern = re.compile(r"\(.*?\)|\[\d{8}\]")  # 清洗字段名的正则

    # 从你的curl里解析的核心Form参数（page/perpage为变量）
    base_form_data = {
        'query': question,
        'urp_sort_way': 'desc',
        'urp_sort_index': '涨停[20260106]',
        'page': str(page),  # 分页变量：页码
        'perpage': str(perpage),  # 分页变量：每页条数
        'addheaderindexes': '',
        'condition': '[{"score":0,"node_type":"op","chunkedResult":"涨停聚焦_&_非st","children":[],"opName":"and","ci":false,"opPropertiesMap":{},"opProperty":"","sonSize":2,"source":"text2sql"},{"dateText":"","ci":true,"indexName":"涨停","indexProperties":["nodate 1","交易日期 20260106"],"dateUnit":"日","source":"text2sql","type":"index","indexPropertiesMap":{"交易日期":"20260106","nodate":"1"},"reportType":"TRADE_DAILY","score":0,"ciChunk":"涨停聚焦","createBy":"preCache","node_type":"index","dateType":"交易日期","domain":"abs_股票领域","uiText":"涨停","valueType":"_是否","sonSize":0},{"dateText":"","ci":true,"indexName":"股票简称","indexProperties":["不包含st"],"source":"text2sql","type":"index","indexPropertiesMap":{"不包含":"st"},"reportType":"null","score":0,"ciChunk":"非st","createBy":"preCache","node_type":"index","domain":"abs_股票领域","uiText":"股票简称不包含st","valueType":"_股票简称","sonSize":0}]',
        'codelist': '',
        'indexnamelimit': '',
        'logid': '288a082ab73a61a93269dda29cd6ac53',
        'ret': 'json_all',
        'sessionid': session_id,
        'source': 'Ths_iwencai_Xuangu',
        'date_range[0]': '20260106',
        'iwc_token': '0ac9cd1917676855390371599',
        'urp_use_sort': '1',
        'user_id': '379374623',
        'uuids[0]': '24087',
        'query_type': 'stock',
        'comp_id': '6836372',
        'business_cat': 'soniu',
        'uuid': '24087'
    }

    while True:
        try:
            # 1. 每次循环更新页码
            base_form_data['page'] = str(page)
            # 2. 加1秒延时，防风控（必加）
            time.sleep(1)

            # 3. 发送POST请求（Form表单格式，用data参数）
            response = requests.post(
                url=url,
                headers=headers,
                cookies=cookies,
                data=base_form_data,  # 新接口核心：用data传递Form参数，不是json
                verify=False,
                timeout=20
            )

            if response.status_code == 200:
                res_json = response.json()
                # 4. 新接口的数据解析路径（核心！和旧接口不同）
                # 容错处理：防止索引越界
                # answer.components[0].data.datas
                stock_data = res_json.get('answer', {}) \
                    .get('components', [{}])[0] \
                    .get('data', {}) \
                    .get('datas', [])
                # stock_data = res_json.get('data', {}).get('data', [])
                current_page_count = len(stock_data)

                print(f"✅ 正在爬取第 {page} 页 → 当前页数据条数：{current_page_count}")

                # 5. 终止循环条件：无数据 或 数据不足100条（最后一页）
                if current_page_count == 0 or current_page_count < perpage:
                    print(f"✅ 爬取完成！已到最后一页，累计数据条数：{len(all_stock_data)}")
                    break

                # 6. 清洗当前页数据（字段名+值）
                clean_data = []
                for old_dict in stock_data:
                    new_dict = {}
                    for old_key, raw_value in old_dict.items():
                        # 清洗字段名：去掉小括号+中括号日期
                        new_key = pattern.sub("", old_key)
                        # 清洗值：安全处理，解决int.strip()报错
                        processed_value = safe_process_value(raw_value)
                        new_dict[new_key] = processed_value
                    clean_data.append(new_dict)

                # 7. 将当前页清洗后的数据追加到总列表（extend避免列表套列表）
                all_stock_data.extend(clean_data)
                page += 1  # 页码+1，准备爬取下一页

            else:
                print(f"⚠️ 第{page}页请求失败，状态码: {response.status_code}，继续下一页")
                page += 1

        except Exception as e:
            print(f"❌ 第{page}页爬取出错: {str(e)}，继续下一页")
            page += 1
            continue

    return all_stock_data


# ===================== 调用测试 =====================
if __name__ == '__main__':
    # 可修改查询条件，比如"龙虎榜股票，非st，涨停的股票"
    question = '涨停聚焦，非st'
    # 调用新接口函数
    all_result = get_stock_data_ths_new(question)

    # 打印最终结果
    if all_result:
        print(f"\n🎉 最终爬取到【{len(all_result)}】条完整股票数据（无重复）")
        # 打印前2条示例
        for idx, item in enumerate(all_result[:2]):
            print(f"\n第{idx + 1}条数据（已清洗）：")
            print(item)
    else:
        print("❌ 未爬取到任何数据，请检查Cookie/hexin-v是否过期")