from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database_orm import get_db
from models import Task

from datetime import date
from sqlalchemy.exc import SQLAlchemyError

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskCreate(BaseModel):
    name: str = Field(min_length=1, description="任务名称不能为空")
    done: bool = False
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: date | None = None


class TaskUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    done: bool | None = None
    priority: Literal["low", "medium", "high"] | None = None
    due_date: date | None = None


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
    db: Session = Depends(get_db),
):
    if page < 1:
        raise HTTPException(status_code=400, detail="页码必须大于 0")

    if size < 1 or size > 100:
        raise HTTPException(status_code=400, detail="每页数量必须在 1 到 100 之间")

        # 1. 收集筛选条件
    conditions = []

    if priority is not None:
        conditions.append(Task.priority == priority)

    if done is not None:
        conditions.append(Task.done == done)

    if due_date is not None:
        conditions.append(Task.due_date == due_date)

    # 2. 统计符合条件的任务总数
    count_statement = (
        select(func.count())
        .select_from(Task)
        .where(*conditions)
    )
    total = db.scalar(count_statement)

    # 3. 设置排序和分页
    sort_column = getattr(Task, sort_by)

    if sort_order == "desc":
        sort_column = sort_column.desc()
    else:
        sort_column = sort_column.asc()

    statement = (
        select(Task)
        .where(*conditions)
        .order_by(sort_column)
        .offset((page - 1) * size)
        .limit(size)
    )
    tasks = db.scalars(statement).all()

    # 4. 保留前端原来使用的返回格式
    return {
        "items": [
            {
                "id": task.id,
                "name": task.name,
                "done": task.done,
                "priority": task.priority,
                "due_date": task.due_date,
            }
            for task in tasks
        ],
        "total": total,
        "page": page,
        "size": size,
        "total_pages": (total + size - 1) // size,
    }

@app.post("/tasks", status_code=201)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    new_task = Task(
        name=task.name,
        done=task.done,
        priority=task.priority,
        due_date=task.due_date,
    )

    try:
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="保存任务失败",
        ) from exc

    return {
        "id": new_task.id,
        "name": new_task.name,
        "done": new_task.done,
        "priority": new_task.priority,
        "due_date": new_task.due_date,
    }


@app.patch("/tasks/{task_id}")
def update_task(
    task_id: int,
    task: TaskUpdate,
    db: Session = Depends(get_db),
):
    update_data = task.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="没有要修改的内容")

    # 这些字段不允许改成空值，截止日期可以清空
    for field in ("name", "done", "priority"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(
                status_code=400,
                detail=f"{field} 不能为 null",
            )

    db_task = db.get(Task, task_id)

    if db_task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    try:
        for field, value in update_data.items():
            setattr(db_task, field, value)

        db.commit()
        db.refresh(db_task)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="修改任务失败",
        ) from exc

    return {
        "id": db_task.id,
        "name": db_task.name,
        "done": db_task.done,
        "priority": db_task.priority,
        "due_date": db_task.due_date,
    }


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = db.get(Task, task_id)

    if db_task is None:
        raise HTTPException(status_code=404, detail="任务不存在")

    try:
        db.delete(db_task)
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="删除任务失败",
        ) from exc

    return {"message": "任务删除成功"}