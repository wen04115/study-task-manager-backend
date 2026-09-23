import sqlite3
from  fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,Field
from fastapi import FastAPI ,HTTPException

app=FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def read_root():
    return {"message":"我的FastAPI后端启动成功！"}

class TaskCreate(BaseModel):
    name:str = Field(min_length=1, description="任务名称不能为空")
    done: bool=False
    priority : str ="medium"
    due_date: str | None =None

class TaskUpdate(BaseModel):
    done:bool    

tasks=[
  {"name": "学习 FastAPI 路由", "done": True},
  {"name": "让前端请求后端", "done": False}  
]
@app.get("/tasks")
def get_tasks():
    connection =  sqlite3.connect("tasks.db")
    cursor = connection.cursor()

    cursor.execute("SELECT id,name,done,priority, due_date FROM tasks")
    rows =cursor.fetchall()

    connection.close()

    db_tasks=[]

    for row in rows:
        db_tasks.append({
            "id": row[0],
            "name": row[1],
            "done": bool(row[2]),
            "priority": row[3],
            "due_date": row[4]
        })

    return db_tasks
@app.post("/tasks",status_code=201)
def create_task(task:TaskCreate):
    connection =  sqlite3.connect("tasks.db")
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO tasks (name ,done,priority,due_date) VALUES (?,?,?,?)",
        (task.name, int(task.done),task.priority, task.due_date)
    )

    connection.commit()

    task_id =cursor.lastrowid

    connection.close()

    return {
        "id": task_id,
        "name": task.name,
        "done": task.done,
        "priority": task.priority,
        "due_date": task.due_date
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.patch("/tasks/{task_id}")
def update_task(task_id:int,task:TaskUpdate):
    connection =sqlite3.connect("tasks.db")
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE tasks SET done =? WHERE id =?",
        (int(task.done),task_id)

    )
    if cursor.rowcount == 0:
        connection.close()
        raise HTTPException(status_code =404, detail="任务不存在")

    connection.commit()
    connection.close()

    return{
        "id":task_id,
        "done": task.done
    }
    
@app.delete("/tasks/{task_id}")
def delete_task(task_id:int):
    connection =sqlite3.connect("tasks.db")
    cursor =connection.cursor()

    cursor.execute(
        "DELETE FROM tasks WHERE id=?",
        (task_id,)
    )

    if cursor.rowcount ==0:
        connection.close()
        raise HTTPException(status_code=404, detail="任务不存在")

    connection.commit()
    connection.close()

    return {
        "message":"任务删除成功"
    }