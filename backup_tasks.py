import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from database_orm import engine
from models import Task


if __name__ == "__main__":
    # 只读取任务，不修改数据库
    with engine.connect() as connection:
        result = connection.execute(
            select(Task.__table__).order_by(Task.id)
        )
        tasks = [dict(row) for row in result.mappings()]

    # 备份保存在当前项目的 outputs 文件夹
    output_dir = Path(__file__).resolve().parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_file = output_dir / f"tasks_backup_{timestamp}.json"

    # x 模式：新建文件，不覆盖已有文件
    with backup_file.open("x", encoding="utf-8") as file:
        json.dump(
            tasks,
            file,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    # 重新读取，检查备份中的任务数量和 ID
    saved_tasks = json.loads(backup_file.read_text(encoding="utf-8"))
    assert len(saved_tasks) == len(tasks)
    assert [task["id"] for task in saved_tasks] == [
        task["id"] for task in tasks
    ]

    print(f"已备份 {len(tasks)} 条任务")
    print(f"备份位置：{backup_file}")