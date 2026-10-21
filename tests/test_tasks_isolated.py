import os
import unittest
import jwt
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database_orm import engine as business_engine, get_db
from main import app
from models import Base, User
from security import create_access_token, verify_password


class IsolatedTaskTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(
            patch.dict(
                os.environ,
                {"JWT_SECRET_KEY": "isolated-test-secret-not-for-real-use-2026"},
            )
        )

        # 若错误地访问业务数据库，立即报错，不建立连接。
        self.enterContext(
            patch.object(
                business_engine,
                "connect",
                side_effect=AssertionError("测试禁止连接真实 MySQL"),
            )
        )

        # 每个测试使用全新的内存数据库。
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(self.engine.dispose)
        Base.metadata.create_all(self.engine)

        with Session(self.engine) as db:
            db.add_all([
                User(id=1, username="test_a", hashed_password="unused"),
                User(id=2, username="test_b", hashed_password="unused"),
            ])
            db.commit()

        def override_db():
            with Session(self.engine) as db:
                yield db

        previous_overrides = app.dependency_overrides.copy()

        def restore_overrides():
            app.dependency_overrides.clear()
            app.dependency_overrides.update(previous_overrides)

        self.addCleanup(restore_overrides)
        app.dependency_overrides[get_db] = override_db

        self.client = self.enterContext(TestClient(app))
        self.headers_a = {
            "Authorization": f"Bearer {create_access_token(1)}"
        }
        self.headers_b = {
            "Authorization": f"Bearer {create_access_token(2)}"
        }

    def create_task(self, name="测试任务"):
        response = self.client.post(
            "/tasks",
            headers=self.headers_a,
            json={"name": name},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def test_login_required(self):
        response = self.client.get("/tasks")
        self.assertEqual(response.status_code, 401)

    def test_name_validation(self):
        for name in ("", "   ", "a" * 256):
            with self.subTest(length=len(name)):
                response = self.client.post(
                    "/tasks",
                    headers=self.headers_a,
                    json={"name": name},
                )
                self.assertEqual(response.status_code, 422)

        task = self.create_task("  学习 Python  ")
        self.assertEqual(task["name"], "学习 Python")

    def test_invalid_date(self):
        response = self.client.get(
            "/tasks",
            headers=self.headers_a,
            params={"due_date": "abc"},
        )
        self.assertEqual(response.status_code, 422)

    def test_create_update_delete(self):
        task = self.create_task()
        url = f"/tasks/{task['id']}"

        response = self.client.patch(
            url,
            headers=self.headers_a,
            json={"name": "已修改", "done": True, "due_date": None},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["name"], "已修改")
        self.assertTrue(response.json()["done"])
        self.assertIsNone(response.json()["due_date"])

        response = self.client.delete(url, headers=self.headers_a)
        self.assertEqual(response.status_code, 200)

        response = self.client.delete(url, headers=self.headers_a)
        self.assertEqual(response.status_code, 404)

    def test_pagination(self):
        for index in range(3):
            self.create_task(f"任务{index}")

        response = self.client.get(
            "/tasks",
            headers=self.headers_a,
            params={"page": 2, "size": 2},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(data["total_pages"], 2)
        self.assertEqual(len(data["items"]), 1)

    def test_other_user_cannot_access(self):
        task = self.create_task()
        url = f"/tasks/{task['id']}"

        response = self.client.get("/tasks", headers=self.headers_b)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 0)

        response = self.client.patch(
            url,
            headers=self.headers_b,
            json={"done": True},
        )
        self.assertEqual(response.status_code, 404)

        response = self.client.delete(url, headers=self.headers_b)
        self.assertEqual(response.status_code, 404)

        response = self.client.get("/tasks", headers=self.headers_a)
        self.assertEqual(response.json()["total"], 1)

    def register_auth_user(self):
        credentials = {
            "username": "auth_test",
            "password": "AuthTestPassword123!",
        }
        response = self.client.post("/auth/register", json=credentials)
        self.assertEqual(response.status_code, 201, response.text)
        return credentials, response.json()

    def test_register_login_and_me(self):
        credentials, registered = self.register_auth_user()

        # 注册响应不应泄露密码或哈希。
        self.assertEqual(set(registered), {"id", "username"})

        # 数据库保存的应该是可验证的哈希，而不是明文。
        with Session(self.engine) as db:
            user = db.get(User, registered["id"])
            self.assertNotEqual(
                user.hashed_password, credentials["password"]
            )
            self.assertTrue(
                verify_password(
                    credentials["password"], user.hashed_password
                )
            )

        response = self.client.post("/auth/login", json=credentials)
        self.assertEqual(response.status_code, 200, response.text)

        login_data = response.json()
        self.assertEqual(login_data["token_type"], "bearer")
        self.assertTrue(login_data["access_token"])

        response = self.client.get(
            "/auth/me",
            headers={
                "Authorization": f"Bearer {login_data['access_token']}"
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), registered)

    def test_duplicate_registration(self):
        credentials, _ = self.register_auth_user()

        response = self.client.post("/auth/register", json=credentials)
        self.assertEqual(response.status_code, 409)

    def test_wrong_password_and_unknown_user(self):
        credentials, _ = self.register_auth_user()

        wrong_password = self.client.post(
            "/auth/login",
            json={
                "username": credentials["username"],
                "password": "WrongPassword123!",
            },
        )
        unknown_user = self.client.post(
            "/auth/login",
            json={
                "username": "not_registered",
                "password": "WrongPassword123!",
            },
        )

        self.assertEqual(wrong_password.status_code, 401)
        self.assertEqual(unknown_user.status_code, 401)
        self.assertEqual(
            wrong_password.json()["detail"],
            unknown_user.json()["detail"],
        )

    def test_invalid_credentials(self):
        expired_token = jwt.encode(
            {"sub": "1", "exp": 0},
            os.environ["JWT_SECRET_KEY"],
            algorithm="HS256",
        )

        tokens = {
            "malformed": "not-a-valid-token",
            "expired": expired_token,
            "missing_user": create_access_token(999999),
        }

        for case, token in tokens.items():
            with self.subTest(case=case):
                response = self.client.get(
                    "/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
                self.assertEqual(response.status_code, 401)
                self.assertEqual(
                    response.headers.get("WWW-Authenticate"),
                    "Bearer",
                )

if __name__ == "__main__":
    unittest.main()