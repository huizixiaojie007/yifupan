from datetime import time, datetime
from typing import Dict, List, Tuple, Union
from schemas.zhangting_info import ZhangtingInfoCreate

# -------------------------- 配置项 --------------------------
# 定义需要过滤的股票名称（可扩展）
FILTERED_GP_NAMES = {"数据来源于：i问财网站（iwencai.com）", "无", "未知", "暂无名称"}
# 时间字段无效值（保持不变）
INVALID_TIME_VALUES = {'undefined', '--', '无', 'N/A', '', ' '}
# ------------------------------------------------------------

def process_time_value(x):
    """处理时间值：无效值返回 None，有效值转为 time 类型
    兼容格式：time对象 / datetime对象 / '09:30:00' / '2025-01-01 09:30:00'
    """
    if not x:
        return None
    # 已经是 time 类型，直接返回
    if isinstance(x, time):
        return x
    # datetime 类型，提取 time 部分
    if isinstance(x, datetime):
        return x.time()
    # 非字符串类型，无法处理
    if not isinstance(x, str):
        return None
    x_strip = x.strip()
    if x_strip in INVALID_TIME_VALUES:
        return None
    # 不包含数字的字符串不可能是时间值（如列名"首次涨停时间"），直接跳过
    if not any(c.isdigit() for c in x_strip):
        return None
    try:
        # 如果包含日期部分（如 '2025-01-01 09:30:00'），先解析为 datetime 再提取 time
        if ' ' in x_strip:
            return datetime.strptime(x_strip, "%Y-%m-%d %H:%M:%S").time()
        return time.fromisoformat(x_strip)
    except Exception as e:
        print(f"警告：时间值[{x}]格式无效，跳过（错误：{e}）")
        return None

# 模糊匹配规则：(关键词列表, 表字段名/字段名列表, 数据处理函数)
MATCH_RULES: List[Tuple[List[str], str | List[str], callable]] = [
    (["股票代码"], "gp_no", lambda x: x.strip() if x and x.strip() else None),
    (["股票简称", "股票名称"], "gp_name", lambda x: x.strip()[:100] if x and x.strip() else None),  # 截断100字符
    (["现价", "最新价"], "curr_price", lambda x: x.strip()[:100] if x and x.strip() else None),
    (["涨跌幅", "最新涨跌幅"], "limitup_range", lambda x: x.strip()[:100] if x and x.strip() else None),
    (["首次涨停时间"], "first_limitup_time", process_time_value),
    (["最终涨停时间"], "last_limitup_time", process_time_value),
    (["连续涨停天数"], "limitup_days", lambda x: x.strip()[:100] if x and x.strip() else None),
    (["涨停原因","涨停原因类别"], "limitup_reason", lambda x: x.strip()[:100] if x and x.strip() else None),  # 截断100字符
    (["原因揭秘"], "limitup_reason_detail", lambda x: x.strip()[:1000] if x and x.strip() else None),  # 截断100字符
    (["涨停封单额"], "limitup_order_amount", lambda x: x.strip()[:100] if x and x.strip() else None),
    (["涨停封成比", "涨停封单量占成交量比"], "limitup_seal_ratio", lambda x: x.strip()[:100] if x and x.strip() else None),
    (["涨停封流比", "涨停封单量占流通a股比"], "limitup_flow_ratio", lambda x: x.strip()[:100] if x and x.strip() else None),
    (["涨停封单量"], "limitup_order_volume", lambda x: x.strip()[:100] if x and x.strip() else None),
    (["涨停开板次数"], "limitup_open_times", lambda x: x.strip()[:10] if x and x.strip() else None),  # 截断10字符
    (["流通市值", "a股市值"], "value", lambda x: x.strip()[:100] if x and x.strip() else None),
    (["几天几板"], "day_limitup", lambda x: x.strip()[:10] if x and x.strip() else None),  # 截断10字符
    (["板块原因"], "sector_reason", lambda x: x.strip()[:100] if x and x.strip() else None),
    (["板块"], "sector", lambda x: x.strip()[:100] if x and x.strip() else None),
    (["换手率"], "turnover_rate", lambda x: x.strip()[:100] if x and x.strip() else None),
    (["板型"], "limitup_type", lambda x: x.strip()[:100] if x and x.strip() else None),
]


def clean_key(raw_key: str) -> str:
    """清洗原始JSON键名（保持不变）"""
    import re
    clean_k = raw_key.replace("\n", "").replace("\r", "")  # 去换行
    clean_k = re.sub(r"\d{4}[-./]\d{2}[-./]\d{2}", "", clean_k)  # 去日期（2025.11.07）
    clean_k = re.sub(r"[()（）]股", "", clean_k)  # 精准删除"(股)""（股）"单位
    clean_k = re.sub(r"[()（）：:元%]", "", clean_k).strip()  # 删其他特殊字符+单位
    return clean_k

def _is_valid_record(raw_dict: Dict) -> bool:
    """判断单条记录是否有效（过滤股票名称为无效值的记录）"""
    # 1. 提取股票名称（支持模糊匹配键名：股票名称/股票简称）
    gp_no = None
    for raw_key, raw_value in raw_dict.items():
        clean_k = clean_key(raw_key)
        if any(keyword in clean_k for keyword in ["股票代码"]):
            gp_no = raw_value.strip() if raw_value and raw_value.strip() else ""
            break

    # 2. 过滤逻辑：股票名称在无效列表中 → 无效记录
    if gp_no in FILTERED_GP_NAMES:
        print(f"过滤无效记录：股票名称为「{gp_no}」（原始数据：{raw_dict.get('股票代码', '无股票代码')}）")
        return False
    return True


def _convert_single_dict(raw_dict: Dict) -> ZhangtingInfoCreate:
    # 先判断记录是否有效，无效直接返回None
    if not _is_valid_record(raw_dict):
        return None
    """内部函数：处理单个字典（单行数据）"""
    schema_kwargs = {}
    for raw_key, raw_value in raw_dict.items():
        clean_k = clean_key(raw_key)
        if not clean_k:
            continue
        for keywords, fields, process_func in MATCH_RULES:
            if any(keyword in clean_k for keyword in keywords):
                try:
                    # 1. 按原有逻辑处理值（字符串走process_func，非字符串保留原值）
                    if isinstance(raw_value, str):
                        temp_value = process_func(raw_value)
                    else:
                        temp_value = raw_value

                    # 2. time类型字段保持None（Pydantic不接受空字符串），其他类型None转空字符串
                    if temp_value is None:
                        processed_value = None if process_func is process_time_value else ""
                    else:
                        processed_value = str(temp_value)
                except Exception as e:
                    print(f"警告：字段[{clean_k}]值[{raw_value}]处理失败：{e}，跳过")
                    processed_value = None
                if isinstance(fields, list):
                    for field in fields:
                        schema_kwargs[field] = processed_value
                else:
                    schema_kwargs[fields] = processed_value
                    break
    return ZhangtingInfoCreate(**schema_kwargs)

def convert_zhangting_json_to_schema(
    raw_data: Union[Dict, List[Dict]]  # 支持输入：单个字典 或 字典列表
) -> Union[ZhangtingInfoCreate, List[ZhangtingInfoCreate]]:
    """适配列表+单个字典：模糊匹配转换为Schema"""
    # 1. 如果是列表（批量数据），循环处理每个字典
    if isinstance(raw_data, list):
        return [_convert_single_dict(item) for item in raw_data if isinstance(item, dict)]
    # 2. 如果是单个字典（单行数据），直接处理
    elif isinstance(raw_data, dict):
        return _convert_single_dict(raw_data)
    # 3. 输入类型错误
    else:
        raise TypeError(f"不支持的输入类型：{type(raw_data)}，仅支持字典或字典列表")
