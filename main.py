import os
import jwt
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, StringConstraints


from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database_orm import get_db
from models import Task, User
from security import hash_password, verify_password, create_access_token

from datetime import date
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TaskName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
    ),
]


class TaskCreate(BaseModel):
    name: TaskName
    done: bool = False
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: date | None = None


class TaskUpdate(BaseModel):
    name: TaskName | None = None
    done: bool | None = None
    priority: Literal["low", "medium", "high"] | None = None
    due_date: date | None = None


class UserCreate(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
    )
    password: str = Field(min_length=8, max_length=128)



class UserLogin(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)

# 从请求头中读取 Bearer 登录凭证
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=401,
        detail="未登录或登录凭证已失效",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 没有携带凭证
    if credentials is None:
        raise unauthorized

    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("请在 .env 中配置 JWT_SECRET_KEY")

    try:
        # 验证签名、过期时间，并要求包含用户 ID
        payload = jwt.decode(
            credentials.credentials,
            secret_key,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        raise unauthorized from exc

    # 凭证对应的用户必须仍存在
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized

    return user    
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
    due_date: date | None = None,
    sort_by: Literal["id", "due_date", "priority"] = "id",
    sort_order: Literal["asc", "desc"] = "desc",
    page: int = 1,
    size: int = 2,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if page < 1:
        raise HTTPException(status_code=400, detail="页码必须大于 0")

    if size < 1 or size > 100:
        raise HTTPException(status_code=400, detail="每页数量必须在 1 到 100 之间")

        # 1. 收集筛选条件
    conditions = [Task.user_id == current_user.id]

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
        .order_by(sort_column, Task.id.asc())
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
def create_task(
    task: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_task = Task(
        name=task.name,
        done=task.done,
        priority=task.priority,
        due_date=task.due_date,
        user_id=current_user.id,
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
    current_user: User = Depends(get_current_user),
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

    db_task = db.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
    )

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
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_task = db.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.user_id == current_user.id,
        )
    )
        
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

@app.post("/auth/register", status_code=201)
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    # 检查用户名是否已存在
    existing_user = db.scalar(
        select(User).where(User.username == user.username)
    )
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="用户名已存在")

    # 只保存密码哈希，不保存原密码
    new_user = User(
        username=user.username,
        hashed_password=hash_password(user.password),
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError as exc:
        db.rollback()

        # MySQL 1062：重复值，同时注册同名账号时也能拦住
        if exc.orig.args[0] == 1062:
            raise HTTPException(
                status_code=409,
                detail="用户名已存在",
            ) from exc

        raise HTTPException(
            status_code=500,
            detail="注册失败",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="注册失败",
        ) from exc

    # 不返回原密码或密码哈希
    return {
        "id": new_user.id,
        "username": new_user.username,
    }

@app.post("/auth/login")
def login_user(user: UserLogin, db: Session = Depends(get_db)):
    # 根据用户名查找用户
    db_user = db.scalar(
        select(User).where(User.username == user.username)
    )

    # 用户不存在，或者密码错误，都返回同一个提示
    if db_user is None:
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
        )

    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="用户名或密码错误",
        )

    # 只有校验通过，才签发登录凭证
    access_token = create_access_token(db_user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@app.get("/auth/me")  # 查看当前登录用户，不返回密码或哈希
def read_current_user(
    current_user: User = Depends(get_current_user),
):
    return {
        "id": current_user.id,
        "username": current_user.username,
    }