from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv  # 用于加载环境变量（需安装 python-dotenv）

# 加载环境变量（从 .env 文件）
load_dotenv()

# 数据库连接配置（优先从环境变量读取，默认值为本地MySQL）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # "mysql+pymysql://root:your_password@localhost:3306/test_db?charset=utf8mb4"
    "mysql+pymysql://yifupan1:Huiyuan809~;@rm-bp1s66uh39wtgzkrllo.mysql.rds.aliyuncs.com:3306/yifupan?charset=utf8mb4"
)

# 初始化SQLAlchemy引擎
engine = create_engine(
    DATABASE_URL,
    echo=True  # 设为True可打印SQL语句（调试用）
)

# 会话工厂（用于创建数据库会话）
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型类（所有ORM模型继承此类）
Base = declarative_base()