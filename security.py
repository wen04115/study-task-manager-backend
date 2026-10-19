import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from dotenv import load_dotenv
from pwdlib import PasswordHash

# 加载项目中的 .env
load_dotenv(Path(__file__).resolve().parent / ".env")

password_hash = PasswordHash.recommended()


# 注册时生成密码哈希
def hash_password(password: str) -> str:
    return password_hash.hash(password)


# 登录时校验密码
def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


# 生成有效期为 30 分钟的登录凭证
def create_access_token(user_id: int) -> str:
    secret_key = os.getenv("JWT_SECRET_KEY")
    if not secret_key:
        raise RuntimeError("请在 .env 中配置 JWT_SECRET_KEY")

    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
    }

    return jwt.encode(payload, secret_key, algorithm="HS256")