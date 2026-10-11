from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import get_db_connection


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, description="任务名称不能为空")
    done: bool = False
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: str | None = None


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    done: bool | None = None
    priority: Literal["low", "medium", "high"] | None = None
    due_date: str | None = None


@app.get("/")
def read_root():
    return {"message": "我的 FastAPI 后端启动成功！"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/tasks")
def get_tasks(
    priority: Literal["low", "medium", "high"] | None = None,
    done: bool | None = None,
    due_date: str | None = None,
    sort_by: Literal["id", "due_date", "priority"] = "id",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = 1,
    size: int = 2,
):
    if page < 1:
        raise HTTPException(status_code=400, detail="页码必须大于 0")

    if size < 1 or size > 100:
        raise HTTPException(status_code=400, detail="每页数量必须在 1 到 100 之间")

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            conditions = []
            params = []

            if priority is not None:
                conditions.append("priority = %s")
                params.append(priority)

            if done is not None:
                conditions.append("done = %s")
                params.append(done)

            if due_date is not None:
                conditions.append("due_date = %s")
                params.append(due_date)
                
            where_sql = ""

            if conditions:
                where_sql = " WHERE " + " AND ".join(conditions)

            # 先查总共有多少条，供前端计算页数
            count_sql = "SELECT COUNT(*) AS total FROM tasks" + where_sql
            cursor.execute(count_sql, params)
            total = cursor.fetchone()["total"]

            # 再查询当前页的数据
            offset = (page - 1) * size

            sql = "SELECT id, name, done, priority, due_date FROM tasks"
            sql += where_sql
            sql += f" ORDER BY {sort_by} {sort_order.upper()}"
            sql += " LIMIT %s OFFSET %s"

            cursor.execute(sql, [*params, size, offset])
            tasks = cursor.fetchall()

            for task in tasks:
                task["done"] = bool(task["done"])

            return {
                "items": tasks,
                "total": total,
                "page": page,
                "size": size,
                "total_pages": (total + size - 1) // size,
            }
    finally:
        connection.close()

@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tasks (name, done, priority, due_date)
                VALUES (%s, %s, %s, %s)
                """,
                (task.name, task.done, task.priority, task.due_date),
            )
            task_id = cursor.lastrowid

        connection.commit()

        return {
            "id": task_id,
            "name": task.name,
            "done": task.done,
            "priority": task.priority,
            "due_date": task.due_date,
        }
    finally:
        connection.close()


@app.patch("/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    update_data = task.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="没有要修改的内容")

    fields = ", ".join(f"{key} = %s" for key in update_data)
    values = list(update_data.values())
    values.append(task_id)

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"UPDATE tasks SET {fields} WHERE id = %s",
                values,
            )

            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="任务不存在")

            cursor.execute(
                """
                SELECT id, name, done, priority, due_date
                FROM tasks
                WHERE id = %s
                """,
                (task_id,),
            )
            updated_task = cursor.fetchone()

        connection.commit()
        updated_task["done"] = bool(updated_task["done"])

        return updated_task
    finally:
        connection.close()


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM tasks WHERE id = %s",
                (task_id,),
            )

            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="任务不存在")

        connection.commit()

        return {"message": "任务删除成功"}
    finally:
        connection.close()