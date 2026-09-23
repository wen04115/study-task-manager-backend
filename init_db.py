import sqlite3

connection = sqlite3.connect("tasks.db")

cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks(
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   name TEXT NOT NULL,
   done INTEGER NOT NULL DEFAULT 0,
   priority TEXT NOT NULL DEFAULT 'MEDIUM',
   due_date TEXT
   )
""")

connection.commit()

connection.close()

print("数据库和tasks表创建成功")

                            