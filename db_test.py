import sqlite3

connection = sqlite3.connect("tasks.db")

cursor = connection.cursor()

cursor.execute(
   "INSERT INTO tasks (name,done) VALUES (?,?)",
   ("学习SQLite  插入数据",0)
)
connection.commit()

cursor.execute("SELECT id,name,done FROM tasks")

rows=cursor.fetchall()

for row in rows:
    print(row)

connection.close()    