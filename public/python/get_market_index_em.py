"""
东方财富大盘指数实时行情爬虫
接口: push2.eastmoney.com/api/qt/ulist.np/get（ulist.np批量查多个secid）
用途: 获取上证指数、深证成指等大盘指数的实时点位、涨跌额、涨跌幅、成交额、上涨家数/下跌家数/平盘家数
防风控: 使用系统curl命令 + 模拟Chrome TLS指纹 + Referer从对应数据页面带过
"""
import subprocess
import time
import json
from typing import List, Dict, Any, Optional


# 常见大盘指数的 secid 预设（secid = 市场号.代码  1=上证, 0=深证, 0=创业板科创板指数也是深证市场）
PRESET_INDEXES = {
    '000001': ('1', '上证指数'),
    '399001': ('0', '深证成指'),
    '399006': ('0', '创业板指'),
    '000688': ('1', '科创50'),
    '000300': ('1', '沪深300'),
    '000016': ('1', '上证50'),
    '000905': ('1', '中证500'),
    '399005': ('0', '中小100'),
    '000011': ('1', '上证基金'),
    '399011': ('0', '深证基金'),
    '399008': ('0', '中小300'),
    '000906': ('1', '中证800'),
    '000852': ('1', '中证1000'),
}


# 东方财富ulist.np返回字段f代码 → 中文含义映射
# 接口: fields=f1,f2,f3,f4,f6,f12,f13,f104,f105,f106
FIELD_MAPPING = [
    ('f12', '指数代码',  lambda x: x if x else '-'),
    ('f13', '市场编号',  lambda x: x if x else '-'),
    ('f1',  '未知字段1', lambda x: x if x else '-'),   # 一般是0或固定值
    ('f2',  '最新点位',  lambda x: x if x not in (None, '-', '') else '-'),
    ('f3',  '涨跌幅(%)', lambda x: x if x not in (None, '-', '') else '-'),
    ('f4',  '涨跌点',    lambda x: x if x not in (None, '-', '') else '-'),
    ('f6',  '成交额',    lambda x: x if x not in (None, '-', '') else '-'),  # 原始单位: 元（需要转亿/万展示）
    ('f104', '上涨家数', lambda x: x if x not in (None, '-', '') else '-'),
    ('f105', '下跌家数', lambda x: x if x not in (None, '-', '') else '-'),
    ('f106', '平盘家数', lambda x: x if x not in (None, '-', '') else '-'),
]
# 注意：东财ulist接口真实字段含义为 f104=上涨、f105=下跌、f106=平盘
# （与get_board_info_em.py一致；曾误标为f105=平盘/f106=下跌导致分布颠倒）


def _format_amount_yuan(raw) -> str:
    """成交额原始单位是「元」，友好格式化 亿/万/元"""
    try:
        num = float(raw)
    except (TypeError, ValueError):
        return '-' if raw in (None, '-', '') else str(raw)
    if num <= 0:
        return '-'
    if num >= 1e8:
        return f"{num / 1e8:.2f}亿"
    if num >= 1e4:
        return f"{num / 1e4:.2f}万"
    return f"{int(num)}元"


def _secids_to_param(index_codes: Optional[List[str]] = None) -> str:
    """把指数代码列表转换为secids参数（自动查表补市场号）"""
    if not index_codes:
        # 默认取前4个常用指数：上证、深证、创业板、科创50
        codes = ['000001', '399001', '399006', '000688']
    else:
        codes = list(index_codes)
    segs = []
    for code in codes:
        if '.' in code:
            # 已经是"市场号.代码"格式，直接用
            segs.append(code)
        else:
            preset = PRESET_INDEXES.get(code)
            if preset:
                segs.append(f"{preset[0]}.{code}")
            else:
                # 默认按代码头猜：6开头=上证1；0/3开头=深证0
                market = '1' if code.startswith('6') else '0'
                segs.append(f"{market}.{code}")
    # secids用半角逗号连接，URL编码
    return ','.join(segs)


def get_market_index_list(
    index_codes: Optional[List[str]] = None,
    extra_fields: Optional[str] = None,
    auto_name: bool = True,
    format_amount: bool = True,
) -> List[Dict[str, Any]]:
    """获取东方财富大盘指数实时行情（上证指数/深证成指等）

    Args:
        index_codes: 指数代码列表，如['000001', '399001']；None则默认上证/深证/创业板/科创50
                     支持原生secid格式（如'1.000001'或'0.399001'）
        extra_fields: 追加fields参数（如要更多f字段自定义），逗号分隔；None使用默认
        auto_name: 是否根据代码自动补中文指数名；默认True
        format_amount: 成交额是否转换亿/万友好单位；True=格式化，False=保留原始「元」

    Returns:
        list: 指数列表，每项包含指数代码、名称、最新点位、涨跌幅、成交额、涨跌家数等
    """
    secids_param = _secids_to_param(index_codes)
    ts = int(time.time() * 1000)
    fields_default = 'f1,f2,f3,f4,f6,f12,f13,f104,f105,f106'
    fields_str = extra_fields if extra_fields else fields_default

    from urllib.parse import quote
    url = (
        f"https://push2.eastmoney.com/api/qt/ulist.np/get"
        f"?cb=jQuery{ts}_{ts + 1}"
        f"&fltt=2"
        f"&secids={quote(secids_param, safe=',')}"
        f"&fields={quote(fields_str, safe=',')}"
        f"&ut=b2884a393a59ad64002292a3e90d46a5"
        f"&_={ts + 2}"
    )

    curl_cmd = [
        'curl', '-sS',
        '-H', 'Accept: */*',
        '-H', 'Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        '-b', 'st_nvi=joLj4La65T-7FxIweyM_26d2f; EMFUND1=null; EMFUND2=null; EMFUND3=null; EMFUND4=null; EMFUND5=null; EMFUND6=null; EMFUND7=null; EMFUND0=null; qgqp_b_id=1c8048dd70664015bac2842fda38aeff; wsc_checkuser_ok=1; st_sn=1; st_pvi=06542231346970; st_sp=2025-11-18%2000%3A29%3A07; st_inirUrl=https%3A%2F%2Fquote.eastmoney.com%2Fcenter%2Fhszs.html;',
        '-H', 'Referer: https://data.eastmoney.com/zjlx/dpzjlx.html',
        '-H', 'Sec-Fetch-Dest: script',
        '-H', 'Sec-Fetch-Mode: no-cors',
        '-H', 'Sec-Fetch-Site: same-site',
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
        '-H', 'sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
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
            print(f"❌ curl执行失败，返回码: {result.returncode}，错误: {result.stderr[:300]}")
            return []

        jsonp_text = result.stdout.strip()
        if not jsonp_text:
            print(f"❌ curl返回为空，stderr: {result.stderr[:300]}")
            return []

        start_idx = jsonp_text.find('{')
        end_idx = jsonp_text.rfind('}')
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            print(f"❌ JSONP格式解析失败，前800字符：{jsonp_text[:800]}")
            return []

        try:
            data = json.loads(jsonp_text[start_idx:end_idx + 1])
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}，截取：{jsonp_text[start_idx:start_idx + 800]}")
            return []

        if not isinstance(data, dict) or data.get('rc') != 0:
            print(f"❌ 指数接口返回异常 rc={data.get('rc')} msg={data.get('msg')}")
            return []

        diff = (data.get('data') or {}).get('diff') or []
        if not isinstance(diff, list) or not diff:
            print("⚠️  指数接口无diff数据")
            return []

        result_list: List[Dict[str, Any]] = []
        for raw in diff:
            if not isinstance(raw, dict):
                continue
            item: Dict[str, Any] = {}
            for fcode, fname, fn in FIELD_MAPPING:
                item[fname] = fn(raw.get(fcode))
            # 自动补中文名称
            if auto_name:
                code = item.get('指数代码', '')
                if code and code in PRESET_INDEXES:
                    item['指数名称'] = PRESET_INDEXES[code][1]
                else:
                    item['指数名称'] = f"指数{code}"
            # 成交额友好格式化
            if format_amount and '成交额' in item:
                item['成交额(原始元)'] = item['成交额']
                item['成交额'] = _format_amount_yuan(item['成交额'])
            # secid还原，方便二次查其他接口
            mkt = item.get('市场编号', None)
            cde = item.get('指数代码', '')
            # 市场编号是字符串"0"/"1"等，不能直接and判断（字符串"0"为假），所以显式判断不是'-'和None
            if mkt not in (None, '-', '') and cde and cde != '-':
                item['secid'] = f"{mkt}.{cde}"
            else:
                # 兜底：用PRESET_INDEXES再查一次secid
                if cde in PRESET_INDEXES:
                    item['secid'] = f"{PRESET_INDEXES[cde][0]}.{cde}"
            result_list.append(item)

        print(f"✅ 大盘指数获取成功，返回 {len(result_list)} 条: {[r.get('指数名称')+':'+str(r.get('最新点位')) for r in result_list]}")
        return result_list

    except subprocess.TimeoutExpired:
        print("❌ curl请求大盘指数超时（15秒）")
        return []
    except FileNotFoundError:
        print("❌ 未找到curl命令")
        return []
    except Exception as e:
        print(f"⚠️  大盘指数请求失败: {str(e)[:200]}（{type(e).__name__}）")
        return []


# ============ 沪深两市涨跌分布 ============

_MARKET_UPDOWN_CACHE = {'ts': 0.0, 'data': None}   # 进程内缓存（60秒），防高频请求触发风控


def _curl_get_json(url: str, referer: str, timeout: int = 15) -> Optional[dict]:
    """系统curl请求JSONP/JSON接口并解析为dict（防风控统一走curl+Chrome头）"""
    ts = int(time.time() * 1000)
    cb = f"jQuery{ts}_{ts + 1}"
    if 'cb=' not in url:
        url = f"{url}{'&' if '?' in url else '?'}cb={cb}&_={ts + 2}"
    curl_cmd = [
        'curl', '-sS',
        '-H', 'Accept: */*',
        '-H', 'Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        '-H', 'Connection: keep-alive',
        '-b', 'st_nvi=joLj4La65T-7FxIweyM_26d2f; nid18=0e655375199c15d554682723df091ba3; nid18_create_time=1781449934286; gviem=zvyUG176w5Ge-grNi0P-Occa5; gviem_create_time=1781449934286; qgqp_b_id=1c8048dd70664015bac2842fda38aeff; wsc_checkuser_ok=1; st_asi=delete; st_pvi=06542231346970; st_sp=2025-11-18%2000%3A29%3A07; st_inirUrl=https%3A%2F%2Fquote.eastmoney.com%2Fcenter%2Fhszs.html; st_sn=86; st_psi=20260827234818103-113200304536-8558292265',
        '-H', f'Referer: {referer}',
        '-H', 'Sec-Fetch-Dest: script',
        '-H', 'Sec-Fetch-Mode: no-cors',
        '-H', 'Sec-Fetch-Site: same-site',
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
        '-H', 'sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        '-H', 'sec-ch-ua-mobile: ?0',
        '-H', 'sec-ch-ua-platform: "macOS"',
        url
    ]
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            print(f"❌ curl请求失败: {result.stderr[:200]}")
            return None
        text = result.stdout.strip()
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        if start_idx == -1 or start_idx >= end_idx:
            print(f"❌ 响应JSON解析失败，前200字符: {text[:200]}")
            return None
        return json.loads(text[start_idx:end_idx + 1])
    except Exception as e:
        print(f"❌ curl请求异常: {str(e)[:150]}")
        return None


def _fetch_hs_fenbu() -> Dict[str, Any]:
    """沪深两市涨跌分布+涨跌停家数（东财涨停板行情页接口，单次请求覆盖沪主板/科创板/深主板/创业板）

    fenbu为涨跌幅整数百分比区间的直方图：key=区间整数（-11~11），value=家数
    其中key=±11即涨停/跌停家数（已实测与东财涨停池/跌停池数量一致）
    注意该接口不含北交所
    """
    data = _curl_get_json(
        'https://push2ex.eastmoney.com/getTopicZDFenBu?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt',
        referer='https://quote.eastmoney.com/ztb/detail'
    )
    up = down = flat = 0
    limit_up = limit_down = 0
    fenbu = ((data or {}).get('data') or {}).get('fenbu') or []
    for bucket in fenbu:
        if not isinstance(bucket, dict):
            continue
        for k, v in bucket.items():
            try:
                pct, cnt = int(k), int(v)
            except (TypeError, ValueError):
                continue
            if pct > 0:
                up += cnt
            elif pct == 0:
                flat += cnt
            else:
                down += cnt
            if pct == 11:
                limit_up += cnt
            elif pct == -11:
                limit_down += cnt
    return {
        'up': up, 'down': down, 'flat': flat,
        'limit_up': limit_up, 'limit_down': limit_down,
    }


def get_market_updown_em() -> Dict[str, Any]:
    """获取沪深两市涨跌分布及涨跌停家数（不含北交所，停牌股不计入）

    数据来源：东财涨停板行情页 getTopicZDFenBu 接口（单次请求）
    返回: up/down/flat(涨跌平家数) + limit_up/limit_down(涨停/跌停家数) + total
    结果缓存60秒
    """
    now = time.time()
    cache = _MARKET_UPDOWN_CACHE
    if cache['data'] and now - cache['ts'] < 60:
        return dict(cache['data'])

    hs = _fetch_hs_fenbu()
    data: Dict[str, Any] = {
        'up': hs['up'], 'down': hs['down'], 'flat': hs['flat'],
        'limit_up': hs['limit_up'], 'limit_down': hs['limit_down'],
        'total': hs['up'] + hs['down'] + hs['flat'],
    }
    if data['total'] > 0:
        cache['ts'] = now
        cache['data'] = data
    print(f"✅ 沪深涨跌分布: 涨{data['up']} 跌{data['down']} 平{data['flat']} "
          f"涨停{data['limit_up']} 跌停{data['limit_down']} 总{data['total']}")
    return data


_LIMIT_INDICATOR_CACHE = {'ts': 0.0, 'data': None}   # 进程内缓存（60秒），防高频请求触发风控

# 指标精选字段中文映射（东财涨停板行情页-指标精选，RPT_CUSTOM_INTSELECTION_LIMIT）
_LIMIT_INDICATOR_LABELS = {
    'TRADE_DATE': '交易日期',
    'LIMIT_NUMBERS': '涨停家数',
    'NATURAL_LIMIT': '自然涨停',
    'DAILY_LIMIT': '一字涨停',          # 口径：涨停总数=自然涨停+该字段（实测82=74+8）
    'TOUCH_LIMIT': '触及涨停',
    'SEALING_RATE': '封板率(%)',
    'SEALING_RATE_YES': '昨日封板率(%)',
    'MONEYMAKING_EFFECT': '赚钱效应(%)',
    'POSITION_SUGGESTION': '仓位建议(%)',
    'NATURAL_LIMIT_YES': '昨日自然涨停',
    'LIMIT_PER_YES': '昨日涨停溢价(%)',
    'T1_PCTCHANGE': '沪指上一交易日涨幅(%)',
    'T2_PCTCHANGE': '沪指前二交易日涨幅(%)',
    'SZZS_5DAYS': '沪指5日均线',
    'SZZS_5DAYS_YES': '沪指5日均线(昨)',
    'SZZS_20DAYS': '沪指20日均线',
    'SZZS_20DAYS_YES': '沪指20日均线(昨)',
    'SZZS_60DAYS': '沪指60日均线',
    'SZZS_60DAYS_YES': '沪指60日均线(昨)',
    'SZZS_250DAYS': '沪指250日均线',
}


def get_limit_indicator_em() -> Dict[str, Any]:
    """获取东财涨停板行情页「指标精选」数据（涨停家数/封板率/赚钱效应/仓位建议/沪指均线等）

    数据来源：datacenter-web.eastmoney.com RPT_CUSTOM_INTSELECTION_LIMIT 报表（单次请求，返回当日一行）
    返回: [{字段英文名, 中文标签, 值}, ...] 按原报表字段顺序
    结果缓存60秒
    """
    now = time.time()
    cache = _LIMIT_INDICATOR_CACHE
    if cache['data'] and now - cache['ts'] < 60:
        return cache['data']

    url = (
        'https://datacenter-web.eastmoney.com/web/api/data/v1/get'
        '?reportName=RPT_CUSTOM_INTSELECTION_LIMIT'
        '&columns=LIMIT_NUMBERS,NATURAL_LIMIT,DAILY_LIMIT,TOUCH_LIMIT,SEALING_RATE,'
        'MONEYMAKING_EFFECT,POSITION_SUGGESTION,NATURAL_LIMIT_YES,LIMIT_PER_YES,'
        'SZZS_5DAYS,SZZS_20DAYS,SZZS_60DAYS,SZZS_5DAYS_YES,SZZS_20DAYS_YES,'
        'SZZS_60DAYS_YES,SZZS_250DAYS,TRADE_DATE,T1_PCTCHANGE,T2_PCTCHANGE,SEALING_RATE_YES'
        '&source=WEB&client=WEB'
    )
    data = _curl_get_json(url, referer='https://quote.eastmoney.com/ztb/?from=center')
    rows = ((data or {}).get('result') or {}).get('data') or []
    if not rows:
        print(f"❌ 指标精选数据获取失败: {str(data.get('message'))[:100] if data else '响应为空'}")
        return []

    row = rows[0]   # 报表仅返回最新交易日一行
    result = [
        {'field': k, 'label': _LIMIT_INDICATOR_LABELS.get(k, k), 'value': v}
        for k, v in row.items()
    ]
    cache['ts'] = now
    cache['data'] = result
    labels_brief = {item['label']: item['value'] for item in result}
    print(f"✅ 指标精选: {labels_brief.get('涨停家数')}涨停 自然{labels_brief.get('自然涨停')} "
          f"封板率{labels_brief.get('封板率(%)')} 赚钱效应{labels_brief.get('赚钱效应(%)')}")
    return result


_MARKET_FUNDFLOW_CACHE = {'ts': 0.0, 'data': None}   # 进程内缓存（300秒），资金流向日线变化不频繁无需高频刷新

# 大盘资金流向日线字段映射（东财 push2his fflow/daykline 接口）
# 金额字段返回单位为元，解析结果一律转为「亿元」
_FUNDFLOW_FIELDS = [
    ('日期', str),
    ('主力净流入', lambda v: round(float(v) / 1e8, 4) if v not in (None, '-', '') else None),
    ('小单净流入', lambda v: round(float(v) / 1e8, 4) if v not in (None, '-', '') else None),
    ('中单净流入', lambda v: round(float(v) / 1e8, 4) if v not in (None, '-', '') else None),
    ('大单净流入', lambda v: round(float(v) / 1e8, 4) if v not in (None, '-', '') else None),
    ('超大单净流入', lambda v: round(float(v) / 1e8, 4) if v not in (None, '-', '') else None),
    ('主力净流入占比', float),
    ('小单占比', float),
    ('中单占比', float),
    ('大单占比', float),
    ('超大单占比', float),
    ('收盘点位', float),
    ('涨跌幅(%)', float),
    ('成交额(亿)', float),   # 实测约14000量级，确认为亿元
    ('其他', lambda v: float(v) if v not in (None, '-', '') else None),
]


def get_market_fundflow_em(days: int = 60) -> List[Dict[str, Any]]:
    """获取沪深两市合并的大盘资金流向日线（东方财富「沪深京资金流向」页接口）

    数据来源：push2his.eastmoney.com /api/qt/stock/fflow/daykline/get
    secid=1.000001(上证) + secid2=0.399001(深证成指) → 两市场合并资金口径
    金额结果统一转换为「亿元」；结果缓存300秒
    """
    now = time.time()
    cache = _MARKET_FUNDFLOW_CACHE
    # 若缓存命中且请求天数不超过缓存里有的天数，直接截断返回
    if cache['data']:
        rows = cache['data']
        if now - cache['ts'] < 300 and len(rows) >= days:
            return rows[-days:]

    url = (
        "https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get"
        "?lmt=0&klt=101"
        "&fields1=f1,f2,f3,f7"
        "&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65"
        "&ut=b2884a393a59ad64002292a3e90d46a5"
        "&secid=1.000001&secid2=0.399001"
    )
    ts = int(time.time() * 1000)
    url = f"{url}&cb=jQuery{ts}_{ts}&_={ts + 1}"
    data = _curl_get_json_full_headers(url, referer='https://data.eastmoney.com/zjlx/dpzjlx.html')
    klines = (((data or {}).get('data') or {}).get('klines')) or []
    structured: List[Dict[str, Any]] = []
    for line in klines:
        if not isinstance(line, str):
            continue
        cols = line.split(',')
        if len(cols) != len(_FUNDFLOW_FIELDS):
            continue
        row = {}
        ok = True
        for (fname, conv), raw in zip(_FUNDFLOW_FIELDS, cols):
            try:
                row[fname] = conv(raw) if callable(conv) else conv(raw)
            except (TypeError, ValueError):
                ok = False
                break
        if ok:
            structured.append(row)
    if structured:
        cache['ts'] = now
        cache['data'] = structured
    print(f"✅ 大盘资金流向: 返回{len(structured)}天；最新({structured[-1]['日期'] if structured else '--'}) "
          f"主力净流入 {structured[-1]['主力净流入'] if structured else '--'}亿")
    return structured[-days:] if days > 0 else structured


# 分时资金流向字段（6列，对应日线f51~f56的前半段：时间/主力/小单/中单/大单/超大单净流入）
# 金额字段返回单位为元，解析结果一律转为「亿元」
_FUNDFLOW_INTRADAY_FIELDS = [
    ('时间', str),
    ('主力净流入', lambda v: round(float(v) / 1e8, 4) if v not in (None, '-', '') else None),
    ('小单净流入', lambda v: round(float(v) / 1e8, 4) if v not in (None, '-', '') else None),
    ('中单净流入', lambda v: round(float(v) / 1e8, 4) if v not in (None, '-', '') else None),
    ('大单净流入', lambda v: round(float(v) / 1e8, 4) if v not in (None, '-', '') else None),
    ('超大单净流入', lambda v: round(float(v) / 1e8, 4) if v not in (None, '-', '') else None),
]

_MARKET_FUNDFLOW_INTRADAY_CACHE = {'ts': 0.0, 'data': None}   # 进程内缓存（30秒），分时刷新较频繁


def get_market_fundflow_intraday_em() -> List[Dict[str, Any]]:
    """获取沪深两市今日分时资金流向（push2.eastmoney.com /api/qt/stock/fflow/kline/get，klt=1分时）

    字段与日线前6列口径一致：时间(HH:MM)、主力/小单/中单/大单/超大单净流入（亿元）
    一个交易日一般返回240根（每分钟1根），结果缓存30秒
    """
    now = time.time()
    cache = _MARKET_FUNDFLOW_INTRADAY_CACHE
    if cache['data'] and now - cache['ts'] < 30:
        return list(cache['data'])

    url = (
        "https://push2.eastmoney.com/api/qt/stock/fflow/kline/get"
        "?lmt=0&klt=1"
        "&fields1=f1,f2,f3,f7"
        "&fields2=f51,f52,f53,f54,f55,f56"
        "&ut=b2884a393a59ad64002292a3e90d46a5"
        "&secid=1.000001&secid2=0.399001"
    )
    data = _curl_get_json_full_headers(url, referer='https://data.eastmoney.com/zjlx/dpzjlx.html')
    klines = (((data or {}).get('data') or {}).get('klines')) or []
    structured: List[Dict[str, Any]] = []
    for line in klines:
        if not isinstance(line, str):
            continue
        cols = line.split(',')
        if len(cols) != len(_FUNDFLOW_INTRADAY_FIELDS):
            continue
        row = {}
        ok = True
        for (fname, conv), raw in zip(_FUNDFLOW_INTRADAY_FIELDS, cols):
            try:
                row[fname] = conv(raw) if callable(conv) else conv(raw)
            except (TypeError, ValueError):
                ok = False
                break
        # 时间字段标准化：取 "HH:MM"（去掉日期前缀），同时保留原始时间作为日期线索
        if ok and '时间' in row:
            t = row['时间']
            parts = str(t).split()
            row['datetime'] = t
            row['时间'] = parts[-1] if parts else t
            if len(parts) >= 2:
                row['日期'] = parts[0]
        if ok:
            structured.append(row)
    if structured:
        cache['ts'] = now
        cache['data'] = structured
    print(f"✅ 大盘资金流向(今日分时): 返回{len(structured)}分钟; "
          f"最新({structured[-1].get('时间') if structured else '--'}) "
          f"主力净流入 {structured[-1].get('主力净流入') if structured else '--'}亿")
    return structured


def _curl_get_json_full_headers(url: str, referer: str, timeout: int = 15) -> Optional[dict]:
    """完整Chrome头的系统curl请求（与用户提供curl一致，用于数据中心接口）"""
    ts = int(time.time() * 1000)
    if 'cb=' not in url:
        url = f"{url}{'&' if '?' in url else '?'}cb=jQuery{ts}_{ts}&_={ts + 2}"
    curl_cmd = [
        'curl', '-sS',
        '-H', 'Accept: */*',
        '-H', 'Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        '-H', 'Connection: keep-alive',
        '-b', 'st_nvi=joLj4La65T-7FxIweyM_26d2f; nid18=0e655375199c15d554682723df091ba3; nid18_create_time=1781449934286; gviem=zvyUG176w5Ge-grNi0P-Occa5; gviem_create_time=1781449934286; qgqp_b_id=1c8048dd70664015bac2842fda38aeff; wsc_checkuser_ok=1; st_pvi=06542231346970; st_sp=2025-11-18%2000%3A29%3A07; st_inirUrl=https%3A%2F%2Fquote.eastmoney.com%2Fcenter%2Fhszs.html; st_sn=260; st_psi=20260831221858154-113200304536-4613679848',
        '-H', f'Referer: {referer}',
        '-H', 'Sec-Fetch-Dest: script',
        '-H', 'Sec-Fetch-Mode: no-cors',
        '-H', 'Sec-Fetch-Site: same-site',
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
        '-H', 'sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        '-H', 'sec-ch-ua-mobile: ?0',
        '-H', 'sec-ch-ua-platform: "macOS"',
        url
    ]
    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            print(f"❌ curl请求失败({referer[:30]}): {result.stderr[:200]}")
            return None
        text = result.stdout.strip()
        s, e = text.find('{'), text.rfind('}')
        if s == -1 or e == -1 or s >= e:
            print(f"❌ JSON解析失败，前200字符: {text[:200]}")
            return None
        return json.loads(text[s:e + 1])
    except Exception as e:
        print(f"❌ curl异常: {str(e)[:150]}")
        return None


_MARGIN_CACHE = {'ts': 0.0, 'data': None}   # 600秒缓存，融资融券日线仅每日一次


def get_margin_rzrq_em(days: int = 60) -> List[Dict[str, Any]]:
    """获取沪深两市融资融券历史每日数据（东方财富数据中心 RPTA_RZRQ_LSHJ）。

    数据来源：datacenter-web.eastmoney.com /api/data/v1/get
    核心字段：RZMRE=融资买入额(元)、RZCHE=融资偿还额(元)、RZJME=融资净买入(元)、
             RZYE=融资余额(元)、RQYE=融券余额(元)、RZRQYE=融资融券余额(元)
    金额结果统一转换为「亿元」；按 DIM_DATE 倒序取最近N日；结果缓存600秒。
    """
    cache = _MARGIN_CACHE
    now = time.time()
    if cache['data'] and (now - cache['ts']) < 600:
        return cache['data'][-days:]   # 取尾部N条（最新数据靠后）

    ts_ms = int(now * 1000)
    # 多取一点再截断，保证缓存里总有更长的数据
    fetch_size = max(days, 120)
    url = (
        'https://datacenter-web.eastmoney.com/api/data/v1/get'
        '?reportName=RPTA_RZRQ_LSHJ'
        '&columns=ALL'
        '&source=WEB'
        '&sortColumns=DIM_DATE'
        '&sortTypes=-1'
        f'&pageNumber=1&pageSize={fetch_size}&filter='
    )
    data = _curl_get_json_full_headers(url, 'https://data.eastmoney.com/rzrq/', timeout=20)
    if not data:
        return cache['data'][-days:] if cache['data'] else []
    rows = (data.get('result') or {}).get('data') or []
    # 原始是倒序的，按时间正序展示
    rows = list(reversed(rows))
    structured = []
    for r in rows:
        def _Y(v):
            return round(float(v) / 1e8, 4) if v not in (None, '-', '') else None
        date_raw = r.get('DIM_DATE', '')
        if isinstance(date_raw, str) and len(date_raw) >= 10:
            date = date_raw[:10]
        else:
            date = str(date_raw)[:10]
        structured.append({
            '日期': date,
            '融资买入额(亿)': _Y(r.get('RZMRE')),
            '融资偿还额(亿)': _Y(r.get('RZCHE')),
            '融资净买入(亿)': _Y(r.get('RZJME')),
            '融资余额(亿)': _Y(r.get('RZYE')),
            '融券余额(亿)': _Y(r.get('RQYE')),
            '两融余额(亿)': _Y(r.get('RZRQYE')),
            '融券偿还量(万股)': round(float(r['RQMCL']) / 1e4, 3) if r.get('RQMCL') not in (None, '-', '') else None,
            '融券卖出量(万股)': round(float(r['RQCHL']) / 1e4, 3) if r.get('RQCHL') not in (None, '-', '') else None,
            '融券余量(万股)': round(float(r['RQYL']) / 1e4, 3) if r.get('RQYL') not in (None, '-', '') else None,
            '融资余额占比(%)': r.get('RZYEZB'),
            '收盘点位': r.get('NEW'),
            '涨跌幅(%)': r.get('ZDF'),
        })
    if structured:
        cache['ts'] = now
        cache['data'] = structured
    latest = structured[-1] if structured else None
    print(f"✅ 两融日线: 返回{len(structured)}条; 最新{latest['日期'] if latest else '--'} 融资买入 "
          f"{latest['融资买入额(亿)'] if latest else '--'}亿")
    return structured[-days:]


def get_index_kline_em(
    secid: str = '1.000001',
    klt: int = 101,
    fqt: int = 1,
    beg: str = '0',
    end: str = '20500101',
    lmt: int = 120,
) -> List[Dict[str, Any]]:
    """获取大盘指数K线数据（上证/深证/创业板等，同样适用于板块和个股secid）

    防风控方案与get_market_index_list一致：使用系统curl + 模拟Chrome头
    注意：beg='0'时东财会忽略lmt返回全部历史，调用方可自行截取尾部N根

    Args:
        secid: 市场号.代码，如'1.000001'(上证)、'0.399001'(深证成指)
        klt: K线周期（101=日线，102=周线，103=月线）
        fqt: 复权类型（0=不复权，1=前复权，2=后复权）
        beg/end: 起止日期（YYYYMMDD），默认全部历史

    Returns:
        list: K线字典列表（日期/开盘价/收盘价/最高价/最低价/成交量/成交额/振幅/涨跌幅/涨跌额/换手率），
              失败或无数据返回空列表
    """
    ts = int(time.time() * 1000)
    from urllib.parse import quote
    url = (
        f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
        f"?cb=jQuery{ts}_{ts + 1}"
        f"&secid={quote(secid)}"
        f"&ut=fa5fd1943c7b386f172d6893dbfba10b"
        f"&fields1=f1,f2,f3,f4,f5,f6"
        f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
        f"&klt={klt}"
        f"&fqt={fqt}"
        f"&beg={beg}"
        f"&end={end}"
        f"&lmt={lmt}"
        f"&_={ts + 2}"
    )

    curl_cmd = [
        'curl', '-sS',
        '-H', 'Accept: */*',
        '-H', 'Accept-Language: zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        '-b', 'qgqp_b_id=dad4df7ea17c871c09b5242823ffebcd; st_nvi=joLj4La65T-7FxIweyM_26d2f; wsc_checkuser_ok=1; st_pvi=06542231346970;',
        '-H', 'Referer: https://quote.eastmoney.com/',
        '-H', 'Sec-Fetch-Dest: script',
        '-H', 'Sec-Fetch-Mode: no-cors',
        '-H', 'Sec-Fetch-Site: same-site',
        '-H', 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36',
        '-H', 'sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        '-H', 'sec-ch-ua-mobile: ?0',
        '-H', 'sec-ch-ua-platform: "macOS"',
        url
    ]

    # fields2(f51-f61) → 中文含义映射
    kline_fields = [
        '日期', '开盘价', '收盘价', '最高价', '最低价',
        '成交量', '成交额', '振幅(%)', '涨跌幅(%)', '涨跌额', '换手率(%)'
    ]

    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=15)
        if result.returncode != 0:
            print(f"❌ curl执行K线失败，返回码: {result.returncode}，错误: {result.stderr[:300]}")
            return []

        jsonp_text = result.stdout.strip()
        if not jsonp_text:
            print(f"❌ K线接口curl返回为空，stderr: {result.stderr[:300]}")
            return []

        start_idx = jsonp_text.find('{')
        end_idx = jsonp_text.rfind('}')
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            print(f"❌ K线JSONP格式解析失败，前500字符：{jsonp_text[:500]}")
            return []

        try:
            data = json.loads(jsonp_text[start_idx:end_idx + 1])
        except json.JSONDecodeError as e:
            print(f"❌ K线JSON解析失败: {e}，截取：{jsonp_text[start_idx:start_idx + 500]}")
            return []

        if not isinstance(data, dict) or data.get('rc') != 0:
            print(f"❌ K线接口返回异常 rc={data.get('rc')} msg={data.get('msg')}")
            return []

        klines = ((data.get('data') or {}).get('klines')) or []
        if not isinstance(klines, list) or not klines:
            print(f"⚠️  secid[{secid}]无K线数据（secid无效或非交易时段）")
            return []

        structured: List[Dict[str, Any]] = []
        for line in klines:
            if not isinstance(line, str) or not line:
                continue
            parts = line.split(',')
            item: Dict[str, Any] = {}
            for i in range(min(len(kline_fields), len(parts))):
                if kline_fields[i] == '日期':
                    item[kline_fields[i]] = parts[i]
                    continue
                try:
                    item[kline_fields[i]] = float(parts[i])
                except ValueError:
                    item[kline_fields[i]] = parts[i]
            structured.append(item)

        print(f"✅ 指数K线获取成功 secid[{secid}]，共 {len(structured)} 条")
        return structured

    except subprocess.TimeoutExpired:
        print("❌ curl请求指数K线超时（15秒）")
        return []
    except FileNotFoundError:
        print("❌ 未找到curl命令")
        return []
    except Exception as e:
        print(f"⚠️  指数K线请求失败: {str(e)[:200]}（{type(e).__name__}）")
        return []


if __name__ == '__main__':
    print("=" * 60)
    print("测试：东方财富大盘指数（默认4大指数）")
    print("=" * 60)
    default = get_market_index_list()
    for i, idx in enumerate(default, 1):
        pct = idx.get('涨跌幅(%)', '-')
        try:
            pct_num = float(pct)
            arrow = '🔴' if pct_num > 0 else ('🟢' if pct_num < 0 else '⚪')
        except (TypeError, ValueError):
            arrow = '⚪'
        print(
            f"\n{i}. {idx.get('指数名称')}({idx.get('指数代码')}) {arrow} {pct}%  涨跌{idx.get('涨跌点')}点"
            f"\n   最新点位: {idx.get('最新点位')}   成交额: {idx.get('成交额')}"
            f"\n   涨{idx.get('上涨家数')}  平{idx.get('平盘家数')}  跌{idx.get('下跌家数')}   secid={idx.get('secid')}"
        )

    print("\n" + "=" * 60)
    print("测试：自定义指数（沪深300 + 中证500 + 中证1000）")
    print("=" * 60)
    custom = get_market_index_list(['000300', '000905', '000852'])
    for i, idx in enumerate(custom, 1):
        print(
            f"{i}. {idx.get('指数名称'):<8}({idx.get('指数代码')}) "
            f"点位:{idx.get('最新点位'):<10}  "
            f"涨跌:{idx.get('涨跌幅(%)')}%  成交额:{idx.get('成交额'):<8}"
        )
