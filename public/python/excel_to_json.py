import unicodedata
from datetime import datetime
from typing import List
from xmlrpc.client import DateTime

import akshare as ak
import pandas as pd
import json

from fastapi import Depends
from sqlalchemy.orm import Session

# from public.python.getApi import get_stock_data_ths, get_ths_limitup
from repositories.zhangting_info_repo import ZhangtingInfoRepo
from schemas.zhangting_info import ZhangtingInfoCreate
from services.zhangting_info_service import ZhangtingInfoService
from utils.data_converter import convert_zhangting_json_to_schema
from config import SessionLocal  # 导入数据库会话工厂
from dataclasses import dataclass

# 依赖：获取数据库会话
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_zhangting_data_batch(schema_list: List[ZhangtingInfoCreate]):
    """批量存储数据到数据库"""
    db = SessionLocal()  # 去掉 next()，直接创建会话

    try:
        service = ZhangtingInfoService(db)
        success_count = 0
        for schema in schema_list:
            try:
                result = service.add_zhangting_info(schema)
                success_count += 1
                print(f"成功存储记录ID：{result.id}（股票代码：{result.gp_no}）")
            except Exception as e:
                print(f"存储失败（股票代码：{schema.gp_no}）：{str(e)}")
                continue
        db.commit()
        print(f"\n批量存储完成！成功：{success_count} 条，失败：{len(schema_list)-success_count} 条")
    except Exception as e:
        db.rollback()
        print(f"批量存储异常：{str(e)}")
    finally:
        db.close()

def update_zhangting_data_batch(schema_list: List[ZhangtingInfoCreate]):
    db = SessionLocal()  # 去掉 next()，直接创建会话
    try:
        service = ZhangtingInfoService(db)
        success_count = 0
        for schema in schema_list:
            try:
                date = datetime.now().date()
                # date_string = "2025-11-13"
                # date = datetime.strptime(date_string, "%Y-%m-%d")
                gp_name = unicodedata.normalize('NFKC', schema.gp_name.replace(' ', ''))
                if(gp_name == '股票简称'):
                    continue
                data = {"gp_name":gp_name,
                        "turnover_rate": schema.turnover_rate,
                        'limitup_type': '换手板' if schema.limitup_type == '--' else schema.limitup_type,
                        'limitup_reason_detail':schema.limitup_reason_detail}
                result = service.update_zhangting_info(gp_name, date, data)
                success_count += 1
                print(f"成功存储（股票代码：{data['gp_name']}）")
            except Exception as e:
                print(f"存储失败（股票代码：{data['gp_name']}）：{str(e)}")
                continue
        db.commit()
        print(f"\n批量存储完成！成功：{success_count} 条，失败：{len(schema_list)-success_count} 条")
    except Exception as e:
        db.rollback()
        print(f"批量存储异常：{str(e)}")
    finally:
        db.close()


def update_zhangting_bankuai_batch(schema_list: List[ZhangtingInfoCreate]):
    db = SessionLocal()  # 去掉 next()，直接创建会话
    try:
        service = ZhangtingInfoService(db)
        success_count = 0
        for schema in schema_list:
            try:
                date = datetime.now().date()
                gp_name = schema['gp_name']
                data = {
                        'sector':schema['sector'],
                        'sector_reason':schema['sector_reason']}
                result = service.update_zhangting_info(gp_name, date, data)
                success_count += 1
                print(f"成功存储记录ID：股票代码：{gp_name}")
            except Exception as e:
                print(f"存储失败（股票代码：{gp_name}）：{str(e)}")
                continue
        db.commit()
        print(f"\n批量存储完成！成功：{success_count} 条，失败：{len(schema_list)-success_count} 条")
    except Exception as e:
        db.rollback()
        print(f"批量存储异常：{str(e)}")
    finally:
        db.close()

# 更新龙虎榜数据
def update_longhu(path):
    longhu = pd.read_excel(path, engine='openpyxl', dtype=str)
    data = longhu.to_dict('records')
    db = SessionLocal()  # 去掉 next()，直接创建会话
    service = ZhangtingInfoService(db)
    for item in data:
        stock_name = item.get('股票简称', '')
        date = datetime.now().date()
        # date_string = "2025-11-13"
        # date = datetime.strptime(date_string, "%Y-%m-%d")
        data = {"longhu":True}
        service.update_zhangting_info(stock_name, date, data)

# 更新得分
def update_score(path):
    # # 1. 读取Excel数据（保留原逻辑，dtype=str避免类型异常）
    # score_df = pd.read_excel(path, engine='openpyxl', dtype=str)
    # score_data = score_df.to_dict('records')  # 修改变量名，避免后续覆盖

    stock_comment_em_df = ak.stock_comment_em()
    score_data = stock_comment_em_df.to_dict('records')  # 修改变量名，避免后续覆盖

    # 2. 初始化数据库会话和服务
    db = SessionLocal()
    service = ZhangtingInfoService(db)
    repo = ZhangtingInfoRepo(db)
    date = datetime.now().date()
    # date = '2025-12-10'

    # 3. 获取目标名称列表，并转为集合（in操作效率更高）
    names = repo.get_name(date)
    # 容错：确保names是可迭代的集合类型（列表/元组→集合）
    target_names = set(names) if isinstance(names, (list, tuple)) else set()

    try:
        # 4. 遍历Excel数据，仅匹配名称时执行更新
        for item in score_data:
            # 提取并标准化股票名称（去空格+统一字符编码）
            stock_name = item.get('名称', '').strip()
            gp_name = unicodedata.normalize('NFKC', stock_name.replace(' ', ''))

            # 核心判定：名称不在目标列表中 → 跳过当前循环
            if not gp_name or gp_name not in target_names:
                print(f"股票名称【{gp_name}】不在目标列表中，跳过更新")
                continue

            # 构造更新数据（避免覆盖外层data变量）
            update_data = {
                "score": item.get('综合得分', '')  # 空值容错
            }

            # 执行数据库更新
            print(f"开始更新股票【{gp_name}】的综合得分：{update_data['score']}")
            service.update_zhangting_info(gp_name, date, update_data)

        # 提交事务（若你的service未自动提交，需手动加：db.commit()）
        # db.commit()
        print("所有匹配的股票得分更新完成")

    except Exception as e:
        # 异常时回滚事务，避免数据不一致
        db.rollback()
        print(f"更新过程中出错：{str(e)}")
        raise  # 可选：抛出异常让上层感知，或仅打印

    finally:
        # 确保数据库会话关闭，释放资源
        db.close()

#更新板块信息
def update_bankuai(path):
    # 读取板块JSON文件（包含name、sector、换手率、版型等字段）
    with open(path, 'r', encoding='utf-8') as f:
        bankuai_data = json.load(f)
    update_zhangting_bankuai_batch(bankuai_data)

def excel_to_update(path):
    # 读取Excel文件（保留原始数据类型，不自动转换）
    df = pd.read_excel(path, engine='openpyxl', dtype=str)
    # 处理NaN：将所有NaN（包括numpy的NaN和字符串'NaN'）替换为空字符串
    df = df.fillna('')
    df = df.replace('NaN', '')
    # 遍历数据，添加板块、换手率、版型信息
    data = df.to_dict('records')
    db: Session = Depends(get_db)
    # 2. 转换为 Schema（自动适配列表/单个字典）
    schema_result = convert_zhangting_json_to_schema(data)
    update_zhangting_data_batch(schema_result)


def excel_to_add(excel_path ):
    # 读取Excel文件（保留原始数据类型，不自动转换）
    df = pd.read_excel(excel_path, engine='openpyxl', dtype=str)
    # 处理NaN：将所有NaN（包括numpy的NaN和字符串'NaN'）替换为空字符串
    df = df.fillna('')
    df = df.replace('NaN', '')
    # 遍历数据，添加板块、换手率、版型信息
    data = df.to_dict('records')

    # path = './batch_stock_result.json'
    # # 读取板块JSON文件（包含name、sector、换手率、版型等字段）
    # with open(path, 'r', encoding='utf-8') as f:
    #     data = json.load(f)

    # question = '涨停聚焦，非st'
    # data = get_ths_limitup(question)

    # 2. 转换为 Schema（自动适配列表/单个字典）
    schema_result = convert_zhangting_json_to_schema(data)

    # 3. 批量存储（如果是列表）或单个存储（如果是单个Schema）
    if isinstance(schema_result, list):
        save_zhangting_data_batch(schema_result)
    else:
        # 单个数据存储（复用之前的逻辑）
        db: Session = next(SessionLocal())
        try:
            service = ZhangtingInfoService(db)
            result = service.add_zhangting_info(schema_result)
            print(f"单个数据存储成功！ID：{result.id}")
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"单个存储失败：{str(e)}")
        finally:
            db.close()


if __name__ == '__main__':
    # excel_file = './涨停聚焦，非st.xlsx'  # 替换为实际Excel路径
    # excel_to_add(excel_file) #增加记录 同花顺数据
    # tongdaxing_path = './首页技术,今日涨停，非st.xlsx'
    # excel_to_update(tongdaxing_path) #更新 通达兴数据
    # bankuai_json_file = '../bankuai.json'  # 板块信息JSON文件路径
    # update_bankuai(bankuai_json_file)
    longhu_path = './龙虎榜股票，非st，涨停的股票.xlsx'
    update_longhu(longhu_path) #更新龙虎榜

    # #更新得分
    # score_path = './stock_comment_em.xlsx'
    # update_score(score_path)
