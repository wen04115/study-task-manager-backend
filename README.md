# 学习任务管理后端

这是一个用 FastAPI 写的学习任务管理后端。

前端可以新增、查看、修改和删除任务。任务数据保存在 MySQL 中。

## 用到的技术

- Python
- FastAPI
- MySQL
- PyMySQL
- python-dotenv

## 已实现功能

- 新增任务
- 查看任务列表
- 修改任务状态、优先级和截止日期
- 删除任务
- 按完成状态筛选
- 按优先级筛选
- 按截止日期筛选
- 按截止日期或编号排序
- 分页查询任务
- 使用 `.env` 保存数据库密码

## 项目文件

```text
main.py             FastAPI 接口
database.py         MySQL 连接代码
test_mysql.py       测试数据库连接
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