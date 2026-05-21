from typing import List, Dict, Optional

from sqlalchemy import desc, func, Integer
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, aliased
from datetime import date

from models.zhangting_info import ZhangtingInfo
from schemas.zhangting_info import ZhangtingInfoCreate

class ZhangtingInfoRepo:
    """用户表数据访问类"""
    def __init__(self, db: Session):
        """初始化数据库会话并加载连续涨停股票数据到内存"""
        self.db = db
        # 启动时加载连续涨停天数大于等于2的股票数据到内存
        self.consecutive_limitup_stocks = self.get_stocks_with_consecutive_limitup()

    def get_by_id(self, id: int) -> ZhangtingInfo:
        """根据ID查询用户"""
        return self.db.query(ZhangtingInfo).filter(ZhangtingInfo.id == id).first()

    def list_by_name(self, gp_name: str) -> List[ZhangtingInfo]:
        """根据股名对应的的所有股票"""
        return self.db.query(ZhangtingInfo).filter(ZhangtingInfo.gp_name == gp_name).order_by(desc(ZhangtingInfo.date)).all()

    def get_date(self) -> List[str]:
        """获取所有有数据的日期（去重、降序，返回 YYYY-MM-DD 字符串列表）"""
        # 关键修复：query() 中指定要查询的列（ZhangtingInfo.date）
        date_list = (
            self.db.query(ZhangtingInfo.date)  # 明确查询 ZhangtingInfo 表的 date 列
            .distinct()  # 去重（避免重复日期）
            .order_by(desc(ZhangtingInfo.date))  # 降序排序（最新日期在前，符合前端需求）
            .all()  # 执行查询，返回 [(date对象,), (date对象,), ...] 格式
        )
        # 转换为 YYYY-MM-DD 字符串（关键：确保返回字符串列表）
        return [str(item[0]) for item in date_list]

    def get_name(self, date: str) -> List[str]:
        """获取某日所有的股票名"""
        # 关键修复：query() 中指定要查询的列（ZhangtingInfo.date）
        date_list = (
            self.db.query(ZhangtingInfo.gp_name)  # 明确查询 ZhangtingInfo 表的 date 列
            .filter(ZhangtingInfo.date == date)
            .all()  # 执行查询，返回 [(date对象,), (date对象,), ...] 格式
        )
        # 转换为 YYYY-MM-DD 字符串（关键：确保返回字符串列表）
        return [str(item[0]) for item in date_list]

    def get_sector_count(self):
        """获取按日期和板块分组的股票数量统计"""
        sector_count_list = (
            self.db.query(ZhangtingInfo.date, ZhangtingInfo.sector, func.count(func.DISTINCT(ZhangtingInfo.gp_no)).label("stock_count"))
            .group_by(ZhangtingInfo.date, ZhangtingInfo.sector)
            .order_by(desc(ZhangtingInfo.date), desc("stock_count"))
            .all()
        )
        
        return [{"date": str(item.date), "sector": item.sector, "stock_count": item.stock_count} for item in sector_count_list]

    def get_sectors(self):
        try:
            # ========== 步骤1：构建子查询（获取每个板块的最新日期+总个股数） ==========
            subquery = self.db.query(
                ZhangtingInfo.sector,
                func.MAX(ZhangtingInfo.date).label("latest_date"),  # 板块最新日期
                func.COUNT(func.DISTINCT(ZhangtingInfo.gp_no)).label("total_stock_count")  # 板块总个股数
            ).group_by(ZhangtingInfo.sector).subquery("sub")  # 子查询别名sub

            # ========== 步骤2：主查询（关联子查询，筛选最新日期数据，统计最新日期个股数） ==========
            # 给主表起别名t1，避免字段冲突
            t1 = aliased(ZhangtingInfo)
            query = self.db.query(
                t1.sector,
                # 取最新日期对应的板块原因（同日期多记录时取任意有效值，通常一致）
                func.MAX(t1.sector_reason).label("sector_reason"),
                # 最新日期当天的个股数
                func.COUNT(func.DISTINCT(t1.gp_no)).label("latest_date_stock_count"),
                # 板块总个股数（来自子查询）
                subquery.c.total_stock_count,
                # 板块最新日期（来自子查询）
                subquery.c.latest_date
            ).join(
                subquery,  # 关联子查询
                # 关联条件：板块相等 + 主表日期=子查询最新日期
                (t1.sector == subquery.c.sector) & (t1.date == subquery.c.latest_date)
            ).group_by(
                t1.sector,
                subquery.c.latest_date,
                subquery.c.total_stock_count
            ).order_by(
                subquery.c.latest_date.desc(),  # 按最新日期降序
                func.COUNT(func.DISTINCT(t1.gp_no)).desc()  # 按最新日期个股数降序
            )

            # print("执行的SQL：", query)  # 打印SQL语句，便于调试
            result = query.all()
            # print("原始结果：", result)

            # ========== 步骤3：转换结果为字典列表（兼容元组/对象格式） ==========
            sectors_list = []
            for item in result:
                # 兼容 SQLAlchemy 元组（item[0]）和对象（item.sector）两种返回格式
                sector = item.sector if hasattr(item, 'sector') else item[0]
                reason = item.sector_reason if hasattr(item, 'sector_reason') else item[1]
                latest_count = item.latest_date_stock_count if hasattr(item, 'latest_date_stock_count') else item[2]
                total_count = item.total_stock_count if hasattr(item, 'total_stock_count') else item[3]
                latest_date = item.latest_date if hasattr(item, 'latest_date') else item[4] if len(item) >= 5 else None

                sectors_list.append({
                    "sector": sector or "",  # 板块名称
                    "sector_reason": reason or "暂无原因",  # 最新日期的板块原因
                    "latest_date_stock_count": int(latest_count) if latest_count else 0,  # 最新日期个股数
                    "total_stock_count": int(total_count) if total_count else 0,  # 板块总个股数
                    "latest_date": latest_date  # 板块最新涨停日期
                })

            return sectors_list
        except Exception as e:
            print("仓库层报错：", str(e))  # 打印具体错误信息，便于排查
            return []  # 兜底返回空列表，避免接口报错


    def get_stocks_by_sector(self, sector:str) -> List[ZhangtingInfo]:
        stocks_list = (
            self.db.query(ZhangtingInfo) .filter(ZhangtingInfo.sector == sector)
            .all()
        )
        # print('stocks_list::',stocks_list)
        return stocks_list

    def get_stocks_with_consecutive_limitup(self):
        """获取连续涨停天数大于等于2的股票，按最大连续涨停天数降序排列"""
        result = (
            self.db.query(
                ZhangtingInfo.gp_name,
                func.max(func.cast(ZhangtingInfo.limitup_days, Integer)).label('max_limitup_days')
            )
            .group_by(ZhangtingInfo.gp_no, ZhangtingInfo.gp_name)
            .having(func.max(func.cast(ZhangtingInfo.limitup_days, Integer)) >= 2)
            .order_by(func.max(func.cast(ZhangtingInfo.limitup_days, Integer)).desc())
            .all()
        )
        return [{'gp_name': item[0], 'max_limitup_days': item[1]} for item in result]

    # 新增：按日期筛选列表
    def list_by_date(self, target_date, skip: int = 0, limit: int = 200) -> List[ZhangtingInfo]:
        """
        按日期查询涨停信息（匹配 create_time 的日期部分）
        :param target_date: 筛选日期（datetime.date类型）
        :param skip: 跳过前n条
        :param limit: 最多返回n条
        :return: 筛选后的记录列表
        """
        return self.db.query(ZhangtingInfo).filter(
                # 提取 create_time 的日期部分，与 target_date 匹配
                ZhangtingInfo.date == target_date).order_by(desc(func.cast(ZhangtingInfo.limitup_days, Integer))).offset(skip).limit(limit).all()

    def update_by_date(
        self,
        target_date: str,
        gp_name: str,
        update_data: Dict[str, str],
    ) -> Optional[bool]:
        try:
            query = self.db.query(ZhangtingInfo).filter(
                ZhangtingInfo.date == target_date,
                (ZhangtingInfo.gp_name == gp_name)
            )
            affected_rows = query.update(update_data, synchronize_session="fetch")
            return affected_rows > 0  # 简化返回：True=有更新，False=无匹配
        except SQLAlchemyError as e:
            print(f"单条更新异常：{str(e)}，日期={target_date}，股票标识={gp_name}")
            raise  # 抛出异常，让批量方法统一处理回滚



    def create(self, zhangting_in: ZhangtingInfoCreate) -> ZhangtingInfo:
        """添加新的涨停信息到数据库"""
        # 将输入数据转换为ORM模型对象
        db_zhangting = ZhangtingInfo(
            gp_no=zhangting_in.gp_no,
            gp_name=zhangting_in.gp_name,
            curr_price=zhangting_in.curr_price,
            limitup_range=zhangting_in.limitup_range,
            first_limitup_time=zhangting_in.first_limitup_time,
            last_limitup_time=zhangting_in.last_limitup_time,
            limitup_days=zhangting_in.limitup_days,
            limitup_reason=zhangting_in.limitup_reason,
            limitup_reason_detail=zhangting_in.limitup_reason_detail,
            limitup_order_volume=zhangting_in.limitup_order_volume,
            limitup_order_amount=zhangting_in.limitup_order_amount,
            limitup_seal_ratio=zhangting_in.limitup_seal_ratio,
            limitup_flow_ratio=zhangting_in.limitup_flow_ratio,
            limitup_open_times=zhangting_in.limitup_open_times,
            value=zhangting_in.value,
            day_limitup=zhangting_in.day_limitup,
            sector=zhangting_in.sector,
            turnover_rate=zhangting_in.turnover_rate,
            limitup_type=zhangting_in.limitup_type,
            sector_reason=zhangting_in.sector_reason,
            date=zhangting_in.date,
            longhu=zhangting_in.longhu,
            longhu_detail=zhangting_in.longhu_detail,
            score=zhangting_in.score
        )
        # 写入数据库
        self.db.add(db_zhangting)
        # self.db.commit()
        # self.db.refresh(db_zhangting)  # 刷新获取自增ID和默认值
        return db_zhangting
