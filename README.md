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
- 用户注册、登录，密码使用 Argon2 哈希保存
- 使用有效期为 30 分钟的 JWT 登录凭证
- 用户只能查询、修改和删除自己的任务

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

然后打开 `.env`，填写 MySQL 配置和 `JWT_SECRET_KEY`。

生成随机签名密钥：

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

将结果填写到本机 `.env`，不要提交真实密码、签名密钥或登录凭证。

## 启动后端

```powershell
uvicorn main:app --reload --port 8000
```

打开接口文档：
http://127.0.0.1:8000/docs

获取任务示例
http://127.0.0.1:8000/tasks?priority=high&done=false&page=1&size=2
这条请求的意思是：查询高优先级、未完成的任务，每页显示 2 条。
任务接口需要登录凭证。请在 `/docs` 中调用 `/auth/login`，再通过 Authorize 设置 token；直接在地址栏访问任务接口不会自动携带凭证。

## 用户认证

- `POST /auth/register`：注册账号
- `POST /auth/login`：登录并获取 JWT
- `GET /auth/me`：获取当前登录用户
- 任务接口通过 `Authorization: Bearer <token>` 验证用户身份
- 凭证过期或无效时返回 401
- 修改或删除不属于当前用户的任务时返回 404

## 接口测试

先启动后端，并通过注册接口准备两个不同的测试账号。

在运行测试的 PowerShell 中设置账号信息，下面的占位文字需要替换：

```powershell
$env:TEST_USERNAME = "测试账号A"
$env:TEST_PASSWORD = "账号A的密码"
$env:TEST_OTHER_USERNAME = "测试账号B"
$env:TEST_OTHER_PASSWORD = "账号B的密码"

python -m unittest discover -s tests -v
```

当前共 8 个测试方法，覆盖任务增删改查、分页校验、条件筛选、空名称校验、未登录访问和跨用户隔离。

测试会创建专用任务，并登记清理操作。请在本地开发环境运行，不要连接生产数据库。

## 数据备份与迁移

- `backup_tasks.py`：将任务数据导出到本机 `outputs` 文件夹
- `create_users_table.py`：创建用户表，不初始化任务表
- `migrate_task_owner.py`：本项目旧数据的一次性迁移脚本，要求用户 1 为 demo_user

迁移脚本不是通用的首次建库脚本，不要在其他数据库上直接执行。
真实 `.env` 和 `outputs` 备份不提交到仓库。