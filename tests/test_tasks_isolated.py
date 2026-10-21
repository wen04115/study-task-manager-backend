import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from database_orm import engine as business_engine, get_db
from main import app
from models import Base, User
from security import create_access_token


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


if __name__ == "__main__":
    unittest.main()