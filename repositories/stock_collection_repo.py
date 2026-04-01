from typing import List, Dict, Optional

from sqlalchemy import desc, insert, func,text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from datetime import date, datetime

from models.stock_collection import StockCollection
from schemas.stock_collection import StockCollectionCreate
class StockCollectionRepo:
    """用户表数据访问类"""
    def __init__(self, db: Session):
        """初始化数据库会话"""
        self.db = db


    def list_by_user_date(self, user: str, date: date) -> List[str]:
        """根据用户名和日期查询"""
        list = self.db.query(StockCollection.gp_name).filter(StockCollection.user == user).filter(StockCollection.date == date).filter(StockCollection.collect == 1).all()
        return [str(item[0]) for item in list]


    def create(self, collect_in: StockCollectionCreate) -> bool:
        """添加新记录：唯一键不冲突则创建，冲突则更新（原生 SQL 修复语法错误）"""
        # 正确语法：INSERT INTO ... VALUES (...) ON DUPLICATE KEY UPDATE ...
        sql = text("""
                    INSERT INTO stock_collection 
                    (gp_name, user, date, collect, create_time, update_time)
                    VALUES (:gp_name, :user, :date, :collect, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        gp_name = VALUES(gp_name),
                        collect = VALUES(collect),
                        update_time = NOW()
                """)

        # 入参字典（与 SQL 中的 :xxx 占位符对应，避免 SQL 注入）
        params = {
            "gp_name": collect_in.gp_name,
            "user": collect_in.user,
            "date": collect_in.date,
            "collect": 1 if collect_in.collect else 0  # 确保是 1/0（适配数据库 tinyint 类型）
        }

        try:
            # 执行原生 SQL
            self.db.execute(sql, params)
            self.db.commit()
            print("创建/更新收藏记录成功")
            return True
        except Exception as e:
            self.db.rollback()
            print(f"创建/更新收藏记录失败：{e}")
            return False


    # def create(self, collect_in: StockCollectionCreate) -> bool:
    #     """添加新的涨停信息到数据库"""
    #     # 将输入数据转换为ORM模型对象
    #     db_collect = StockCollection(
    #         gp_name=collect_in.gp_name,
    #         user=collect_in.user,
    #         date=collect_in.date,
    #         collect=collect_in.collect,
    #         create_time=datetime.now(),
    #         update_time=datetime.now()
    #     )
    #     # 写入数据库
    #     self.db.add(db_collect)
    #     self.db.commit()
    #     # self.db.refresh(db_zhangting)  # 刷新获取自增ID和默认值
    #     return db_collect


    # @staticmethod
    # def get_collection_status(user: str, gp_no: str, date: str) -> bool:
    #     """查询收藏状态（仅操作数据库，无业务逻辑）"""
    #     conn = get_db_connection()
    #     if not conn:
    #         return False
    #
    #     try:
    #         with conn.cursor() as cursor:
    #             sql = """
    #                 SELECT collect FROM stock_collection
    #                 WHERE user = %s AND gp_no = %s AND date = %s
    #                 LIMIT 1
    #             """
    #             cursor.execute(sql, (user, gp_no, date))
    #             result = cursor.fetchone()
    #             # collect 字段是 tinyint(1)：1=收藏，0=未收藏
    #             return result["collect"] == 1 if result else False
    #     finally:
    #         conn.close()
    #
    # @staticmethod
    # def upsert_collection(req: ToggleCollectionReq) -> Tuple[bool, str]:
    #     """新增/更新收藏状态（幂等操作，利用唯一索引）"""
    #     conn = get_db_connection()
    #     if not conn:
    #         return False, "数据库连接失败"
    #
    #     try:
    #         with conn.cursor() as cursor:
    #             # 利用唯一索引（user+gp_no+date）实现：存在则更新，不存在则新增
    #             sql = """
    #                 INSERT INTO stock_collection
    #                 (gp_no, gp_name, date, user, collect)
    #                 VALUES (%s, %s, %s, %s, %s)
    #                 ON DUPLICATE KEY UPDATE
    #                     gp_name = VALUES(gp_name),
    #                     collect = VALUES(collect),
    #                     update_time = CURRENT_TIMESTAMP
    #             """
    #             # collect 字段：True→1，False→0
    #             collect_val = 1 if req.isCollect else 0
    #             cursor.execute(
    #                 sql,
    #                 (req.gpNo, req.gpName, req.date, req.user, collect_val)
    #             )
    #         conn.commit()
    #         msg = "收藏成功" if req.isCollect else "取消收藏成功"
    #         return True, msg
    #     except Exception as e:
    #         conn.rollback()
    #         print(f"数据库操作失败：{e}")
    #         return False, f"操作失败：{str(e)}"
    #     finally:
    #         conn.close()


# 单例实例
# stock_collection_repo = StockCollectionRepo()