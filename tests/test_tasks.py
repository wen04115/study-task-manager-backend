import unittest
import requests
from uuid import uuid4

class TaskTests(unittest.TestCase):
    def test_list_tasks(self):  #检查任务列表和分页结果是否正常
        response = requests.get(
            "http://127.0.0.1:8000/tasks",
            params={"page": 1, "size": 2},
            timeout=10,
        )

        self.assertEqual(response.status_code, 200, response.text)

        data = response.json()
        self.assertIsInstance(data["items"], list)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["size"], 2)
        self.assertLessEqual(len(data["items"]), 2)

    def test_reject_invalid_page(self):  #检查页码为 0 时是否返回 400
        response = requests.get(
            "http://127.0.0.1:8000/tasks",
            params={"page": 0},
            timeout=10,
        )

        self.assertEqual(response.status_code, 400, response.text)
        self.assertEqual(
            response.json()["detail"],
            "页码必须大于 0",
        )    

    def test_reject_invalid_size(self):  #检查每页条数为 0 或 101 时是否返回 400
        for size in (0, 101):
            with self.subTest(size=size):
                response = requests.get(
                    "http://127.0.0.1:8000/tasks",
                    params={"size": size},
                    timeout=10,
                )

                self.assertEqual(
                    response.status_code,
                    400,
                    response.text,
                ) 

        
    def delete_test_task(self, task_id): # 清理本次测试创建的任务，不会被当作独立测试
        response = requests.delete(
            f"http://127.0.0.1:8000/tasks/{task_id}",
            timeout=10,
        )
        self.assertEqual(response.status_code, 200, response.text)

    
    def test_filter_tasks(self):  # 创建不同条件的任务，检查筛选是否正确
        url = "http://127.0.0.1:8000/tasks"
        task_ids = []

        # 第一条应被查到，后两条不应被查到
        conditions = [
            ("high", False),
            ("high", True),
            ("low", False),
        ]

        for priority, done in conditions:
            created = requests.post(
                url,
                json={
                    "name": f"筛选测试_{uuid4().hex}",
                    "priority": priority,
                    "done": done,
                },
                timeout=10,
            )
            self.assertEqual(created.status_code, 201, created.text)

            task_id = created.json()["id"]
            self.addCleanup(self.delete_test_task, task_id)
            task_ids.append(task_id)

        response = requests.get(
            url,
            params={
                "priority": "high",
                "done": "false",
                "sort_by": "id",
                "sort_order": "desc",
                "page": 1,
                "size": 100,
            },
            timeout=10,
        )
        self.assertEqual(response.status_code, 200, response.text)

        tasks = response.json()["items"]
        returned_ids = [task["id"] for task in tasks]

        self.assertIn(task_ids[0], returned_ids)
        self.assertNotIn(task_ids[1], returned_ids)
        self.assertNotIn(task_ids[2], returned_ids)

        for task in tasks:
            self.assertEqual(task["priority"], "high")
            self.assertIs(task["done"], False)

    def test_reject_empty_name(self):  #检查新增任务名称为空时是否返回 422
        response = requests.post(
            "http://127.0.0.1:8000/tasks",
            json={"name": ""},
            timeout=10,
        )

        self.assertEqual(response.status_code, 422, response.text)

        errors = response.json()["detail"]
        self.assertTrue(
            any(error["loc"] == ["body", "name"] for error in errors),
            response.text,
        ) 

        
    def test_create_update_delete_task(self):  # 检查新增、修改和删除任务是否正常
        url = "http://127.0.0.1:8000/tasks"
        name = f"自动化测试_{uuid4().hex}"

        created = requests.post(
            url,
            json={"name": name},
            timeout=10,
        )
        self.assertEqual(created.status_code, 201, created.text)

        task_id = created.json()["id"]

        try:
            self.assertEqual(created.json()["name"], name)

            updated = requests.patch(
                f"{url}/{task_id}",
                json={"done": True},
                timeout=10,
            )
            self.assertEqual(updated.status_code, 200, updated.text)
            self.assertIs(updated.json()["done"], True)
            self.assertEqual(updated.json()["name"], name)
        finally:
            deleted = requests.delete(
                f"{url}/{task_id}",
                timeout=10,
            )
            self.assertEqual(deleted.status_code, 200, deleted.text)                              