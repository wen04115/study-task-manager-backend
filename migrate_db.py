import sqlite3

connection = sqlite3.connect("tasks.db")
cursor =connection.cursor()

cursor.execute("PRAGMA table_info(tasks)")
columns = [column[1] for column in cursor.fetchall()]

if "priority" not in columns:
    cursor.execute(
        "ALTER TABLE tasks ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'"
    )

if "due_date" not in columns:
    cursor.execute(
        "ALTER TABLE tasks ADD COLUMN due_date TEXT"
    )    

connection.commit()

connection.close()

print("任务表字段迁移成功")