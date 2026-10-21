# 学习任务管理后端

基于 FastAPI 和 MySQL 的学习任务管理系统后端，为前端提供任务创建、查询、修改、删除及筛选分页接口。

## 关联仓库

前端：[study-task-manager-frontend](https://github.com/wen04115/study-task-manager-frontend)

## 技术栈

- Python 3.12、FastAPI、Pydantic
- MySQL、SQLAlchemy、PyMySQL
- PyJWT：JWT 登录认证
- pwdlib / Argon2：密码哈希
- python-dotenv：加载环境配置
- unittest、FastAPI TestClient、HTTPX：自动化测试
- SQLite 内存数据库：隔离测试
- GitHub Actions：持续集成
- Docker：后端镜像构建与容器化运行

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
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
}
```

然后打开 `.env`，填写 MySQL 配置和 `JWT_SECRET_KEY`。

生成随机签名密钥：

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

将结果填写到本机 `.env`，不要提交真实密码、签名密钥或登录凭证。

## 首次初始化数据库

先在 MySQL 中创建数据库，名称与 `.env` 的 `MYSQL_DATABASE` 一致，并填写正确的连接配置。

安装 Python 依赖、配置 `.env` 后，在项目根目录执行：

```powershell
python init_tables.py
```

脚本会根据 ORM 模型创建缺失的 users、tasks 表，不删除已有数据，也不会修改已有表结构。

旧的 `init_db.py` 是 SQLite 版本，不用于当前 MySQL 项目的初始化。
已有数据库的结构变更需要单独迁移，不能依赖初始化脚本完成。

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

## 自动化测试

推荐使用 Python 3.12。在项目根目录安装业务依赖和测试客户端依赖：

```powershell
python -m pip install -r requirements.txt
python -m pip install httpx==0.28.1
```

运行隔离测试：

```powershell
python -B -m unittest discover -s tests -p "test_tasks_isolated.py" -v
```

当前包含 10 项测试，覆盖：

- 未登录访问拦截
- 任务名称校验及首尾空格处理
- 非法日期校验
- 任务创建、修改、删除
- 分页查询
- 跨用户访问隔离
- 注册、密码哈希、登录及当前用户查询
- 重复注册拦截
- 错误密码和不存在的用户
- 非法、过期及对应用户不存在的登录凭证

隔离测试使用 SQLite 内存数据库和临时测试用户，不需要启动后端服务，
不使用真实账号，并阻止连接业务 MySQL。

这些测试不替代真实 MySQL 兼容性测试。

### 可选：真实服务集成测试

原来的 tests/test_tasks.py 请求本地正在运行的后端，
需要通过 TEST_USERNAME、TEST_PASSWORD、
TEST_OTHER_USERNAME、TEST_OTHER_PASSWORD 配置两个专用测试账号。

只运行该文件：

```powershell
python -m unittest discover -s tests -p "test_tasks.py" -v
```

这组测试会向服务对应的数据库写入测试任务并尝试清理。
只能连接专用开发或测试数据库，不得连接生产数据库。

不要使用不带文件筛选条件的 discover 命令，
避免意外同时运行真实服务测试。

## 持续集成 CI

工作流文件：.github/workflows/ci.yml。

推送到 main、向 main 发起 Pull Request 或手动触发时，执行：

1. 安装 Python 依赖及测试客户端。
2. 检查依赖兼容性。
3. 运行隔离测试。

CI 不依赖本机 MySQL，也不需要配置真实账号或数据库密码。
结果可在本仓库的 Actions 页面查看。

CI 通过只代表上述检查通过，不代表完成了生产部署或所有场景验收。


## Docker Compose 本地部署

适用于 Windows Docker Desktop。

- 前端由 Nginx 提供静态页面。
- 后端由 Uvicorn 运行 FastAPI。
- Compose 编排前后端服务。
- 后端连接宿主机现有 MySQL，不创建或迁移数据库。
- 真实 .env 不写入镜像、不提交到 Git。

### 准备条件

1. Docker Desktop 和宿主机 MySQL 已启动。
2. 后端 .env 已配置数据库账号、端口、数据库名和 JWT_SECRET_KEY。
3. 数据库表结构已准备好。
4. 前后端仓库均已下载，并包含各自的 Dockerfile。

### 首次构建与启动

在后端项目根目录执行，将前端路径替换为实际位置：

```powershell
$env:FRONTEND_CONTEXT = 'D:/codex_create/ai-study-react'

docker compose config --quiet
docker compose build
docker compose up -d --no-build
docker compose ps
```

FRONTEND_CONTEXT 仅在当前终端有效，新开终端后需要重新设置。

访问页面：http://127.0.0.1:8080

健康检查：http://127.0.0.1:8080/api/health

后端不发布宿主机端口；Nginx 在容器网络内转发 /api 请求。
容器中的 MYSQL_HOST 覆盖为 host.docker.internal，本机 .env 无须修改。

### 日常启动与停止

在后端项目根目录设置 FRONTEND_CONTEXT 后执行：

启动：

```powershell
docker compose up -d --no-build
```

停止时再单独执行：

```powershell
docker compose stop
```

### 修改代码后重新部署

```powershell
docker compose build
docker compose up -d --no-build
```

仅重启容器不会更新镜像中的代码。

### 数据与验收范围

任务保存在外部 MySQL，不保存在前后端容器中。
容器重建不会自动删除外部 MySQL 数据，但仍应独立做好数据库备份。

已完成本地页面登录、任务读写、刷新登录恢复，
以及容器重建后任务和修改保留的手动验收。

/health 只检查应用响应，不检查 MySQL。
登录和任务操作成功才构成数据库连通性的验证。

本地验收不等于公网生产部署验收。