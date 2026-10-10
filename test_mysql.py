from database import get_db_connection

connection = get_db_connection()

try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT DATABASE() AS database_name")
        result = cursor.fetchone()
        print("连接成功，当前数据库：", result["database_name"])
finally:
    connection.close()