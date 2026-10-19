from sqlalchemy import inspect

from database_orm import engine
from models import Base


if __name__ == "__main__":
    # 根据 ORM 模型创建缺失的表，不删除已有表
    Base.metadata.create_all(bind=engine, checkfirst=True)

    inspector = inspect(engine)

    for table_name in ("users", "tasks"):
        columns = inspector.get_columns(table_name)
        print(table_name, [column["name"] for column in columns])

    print("数据库表初始化完成")