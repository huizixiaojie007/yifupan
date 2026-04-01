# from config import SessionLocal, engine, Base
# from services.zhangting_info_service import UserService
# from schemas import UserCreate, UserUpdate
# from sqlalchemy.orm import Session
#
# # 初始化数据库表（首次运行时创建表结构）
# Base.metadata.create_all(bind=engine)
#
#
# def get_db() -> Session:
#     """获取数据库会话（自动关闭）"""
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
#
#
# def main():
#     # 获取数据库会话
#     db = next(get_db())
#
#     # 初始化业务层
#     user_service = UserService(db)
#
#     try:
#         # 1. 注册新用户
#         user_in = UserCreate(
#             username="test_user",
#             email="test@example.com",
#             password="123456"  # 实际项目中密码应更复杂
#         )
#         new_user = user_service.register(user_in)
#         print(f"注册成功：{new_user}")
#
#         # 2. 查询用户
#         user = user_service.get_user(new_user.id)
#         print(f"查询用户：{user}")
#
#         # 3. 更新用户邮箱
#         update_in = UserUpdate(email="updated@example.com")
#         updated_user = user_service.update_user(user.id, update_in)
#         print(f"更新后：{updated_user}")
#
#         # 4. 删除用户（演示用，实际可注释）
#         # delete_result = user_service.delete_user(user.id)
#         # print(f"删除结果：{delete_result}")
#
#     except Exception as e:
#         print(f"操作失败：{e}")
#     finally:
#         db.close()
#
#
# if __name__ == "__main__":
#     main()