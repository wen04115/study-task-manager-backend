import os
from pathlib import Path
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

load_dotenv(Path(__file__).resolve().parent / ".env")

database_url = URL.create(
    drivername="mysql+pymysql",  #数据库用 MySQL，底层驱动用 PyMySQL
    username=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    host=os.getenv("MYSQL_HOST"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    database=os.getenv("MYSQL_DATABASE"),
    query={"charset": "utf8mb4"},
)

engine = create_engine(database_url)
def get_db():
    with Session(engine) as session:
        yield session
        
if __name__ == "__main__":
    with engine.connect() as connection:
        result = connection.execute(text("SHOW COLUMNS FROM tasks"))

        for column in result.mappings():
            print(dict(column))