from sqlalchemy import inspect, text

from database_orm import engine


if __name__ == "__main__":
    with engine.connect() as connection:
        # 确认任务将归属给正确的用户
        username = connection.scalar(
            text("SELECT username FROM users WHERE id = :id"),
            {"id": 1},
        )
        if username != "demo_user":
            raise RuntimeError("用户 1 不是 demo_user，停止迁移")

        # 防止重复执行
        columns = inspect(connection).get_columns("tasks")
        if any(column["name"] == "user_id" for column in columns):
            raise RuntimeError("user_id 已存在，请先核对，不要重复迁移")

        # 记录原有任务内容
        original_tasks = connection.execute(
            text(
                "SELECT id, name, done, priority, due_date "
                "FROM tasks ORDER BY id"
            )
        ).all()

        # 先增加允许为空的归属字段和外键
        connection.execute(text("""
            ALTER TABLE tasks
            ADD COLUMN user_id INT NULL,
            ADD CONSTRAINT fk_tasks_user
                FOREIGN KEY (user_id) REFERENCES users(id)
        """))

        # 将现有任务归到 demo_user
        connection.execute(
            text("UPDATE tasks SET user_id = :id WHERE user_id IS NULL"),
            {"id": 1},
        )
        connection.commit()

        # 填好旧数据后，要求以后的任务必须有归属
        connection.execute(text(
            "ALTER TABLE tasks MODIFY COLUMN user_id INT NOT NULL"
        ))

        # 检查原有任务内容没有改变
        current_tasks = connection.execute(
            text(
                "SELECT id, name, done, priority, due_date "
                "FROM tasks ORDER BY id"
            )
        ).all()
        if current_tasks != original_tasks:
            raise RuntimeError("任务内容检查不一致，请停止后续操作")

        owned_count = connection.scalar(
            text("SELECT COUNT(*) FROM tasks WHERE user_id = :id"),
            {"id": 1},
        )

        print(f"迁移完成，用户 1 拥有 {owned_count} 条任务")
        print("原有任务内容检查通过")