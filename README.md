# 学习任务管理后端

基于 FastAPI 和 MySQL 的学习任务管理系统后端，为前端提供任务创建、查询、修改、删除及筛选分页接口。

## 关联仓库

前端：[study-task-manager-frontend](https://github.com/wen04115/study-task-manager-frontend)

## 技术栈

- Python
- FastAPI
- MySQL
- PyMySQL
- python-dotenv
- SQLAlchemy：数据库表映射、查询和事务操作

## 核心功能

- 任务新增、查询、修改、删除
- 修改任务完成状态、优先级和截止日期
- 按完成状态、优先级、截止日期筛选任务
- 按截止日期或编号排序
- 分页查询任务
- 使用 `.env` 管理 MySQL 连接配置
- 使用参数化 SQL 执行数据库查询

## 项目文件

```text
main.py             FastAPI 接口与业务逻辑
database.py         MySQL 连接代码
test_mysql.py       MySQL 连接测试
.env.example        数据库配置示例
database_orm.py     SQLAlchemy 连接引擎和会话
models.py           任务表 ORM 模型
requirements.txt    Python 依赖清单
```

## 启动项目

先安装依赖：

```powershell
python -m pip install -r requirements.txt
```

复制配置文件：

```powershell
Copy-Item .env.example .env
```

然后打开 `.env`，填写自己的 MySQL 密码。

## 启动后端

```powershell
uvicorn main:app --reload --port 8000
```

打开接口文档：
http://127.0.0.1:8000/docs

获取任务示例
http://127.0.0.1:8000/tasks?priority=high&done=false&page=1&size=2
这条请求的意思是：查询高优先级、未完成的任务，每页显示 2 条。

## 接口测试

先启动后端，再在项目根目录执行：

```powershell
$env:NO_PROXY = "127.0.0.1,localhost"
python -m unittest discover -s tests -v
```

测试使用 unittest 和 requests，覆盖任务查询、分页校验、条件筛选、空名称校验，以及新增、修改和删除流程。

测试会创建专用任务，并在清理步骤中删除。