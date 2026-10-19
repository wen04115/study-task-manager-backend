from sqlalchemy import inspect

from database_orm import engine
from models import User


if __name__ == "__main__":
    # 只创建 users 表；已存在时跳过
    User.__table__.create(bind=engine, checkfirst=True)

    # 查看实际创建的字段
    for column in inspect(engine).get_columns("users"):
        print(column["name"], column["type"])