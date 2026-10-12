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


##启动项目
先安装依赖：
pip install fastapi uvicorn pymysql python-dotenv

复制配置文件：
Copy-Item .env.example .env

然后打开 .env，填写自己的 MySQL 密码。

##启动后端：
uvicorn main:app --reload --port 8000

打开接口文档：
http://127.0.0.1:8000/docs

获取任务示例
http://127.0.0.1:8000/tasks?priority=high&done=false&page=1&size=2
这条请求的意思是：查询高优先级、未完成的任务，每页显示 2 条。
