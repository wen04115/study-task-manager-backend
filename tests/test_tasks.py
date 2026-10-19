import unittest
import requests
import os
from uuid import uuid4


class TaskTests(unittest.TestCase):
    # 每个测试开始前，先登录并保存凭证
    def setUp(self):
        self.client = requests.Session()
        self.addCleanup(self.client.close)
        self.client.trust_env = False

        response = self.client.post(
            "http://127.0.0.1:8000/auth/login",
            json={
                "username": os.environ["TEST_USERNAME"],
                "password": os.environ["TEST_PASSWORD"],
            },
            timeout=10,
        )
        self.assertEqual(response.status_code, 200, response.text)

        token = response.json()["access_token"]
        self.client.headers.update({
            "Authorization": f"Bearer {token}",
        })



    def test_list_tasks(self):  #检查任务列表和分页结果是否正常
        response = self.client.get(
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
        response = self.client.get(
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
                response = self.client.get(
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
        response = self.client.delete(
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
            created = self.client.post(
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
            self.addCleanup(self.delete_test_task, task_id) # addCleanup 登记测试结束后执行的操作
            task_ids.append(task_id)

        response = self.client.get(
            url,
            params={  #params就是查询条件
                "priority": "high", # 只查高优先级
                "done": "false",
                "sort_by": "id",  # 按任务 ID 排序
                "sort_order": "desc",
                "page": 1,  # 查询第 1 页
                "size": 100,  # 每页最多 100 条
            },
            timeout=10,
        )
        self.assertEqual(response.status_code, 200, response.text)

        tasks = response.json()["items"]
        returned_ids = [task["id"] for task in tasks]

        self.assertIn(task_ids[0], returned_ids)  #assertIn(a, b) 检查 a 是否在 b 里面
        self.assertNotIn(task_ids[1], returned_ids)  #检查指定值是否不在结果中
        self.assertNotIn(task_ids[2], returned_ids)   #检查第三条任务不在结果中

        for task in tasks:
            self.assertEqual(task["priority"], "high")
            self.assertIs(task["done"], False)

    def test_reject_empty_name(self):  #检查新增任务名称为空时是否返回 422
        response = self.client.post(
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

        created = self.client.post(
            url,
            json={"name": name},
            timeout=10,
        )
        self.assertEqual(created.status_code, 201, created.text)

        task_id = created.json()["id"]

        try:
            self.assertEqual(created.json()["name"], name)

            updated = self.client.patch(
                f"{url}/{task_id}",
                json={"done": True},
                timeout=10,
            )
            self.assertEqual(updated.status_code, 200, updated.text)
            self.assertIs(updated.json()["done"], True)
            self.assertEqual(updated.json()["name"], name)
        finally:
            deleted = self.client.delete(
                f"{url}/{task_id}",
                timeout=10,
            )
            self.assertEqual(deleted.status_code, 200, deleted.text) 

        # 检查未登录时不能查询任务
    def test_list_requires_login(self):
        response = self.client.get(
            "http://127.0.0.1:8000/tasks",
            headers={"Authorization": None},
            timeout=10,
        )

        self.assertEqual(response.status_code, 401, response.text)
        self.assertEqual(
            response.json()["detail"],
            "未登录或登录凭证已失效",
        )  

        # 检查其他用户不能修改或删除自己的任务
    def test_reject_other_user_operations(self):
        url = "http://127.0.0.1:8000"

        # 登录另一个账号，不改变 self.client 原来的授权
        login = self.client.post(
            f"{url}/auth/login",
            json={
                "username": os.environ["TEST_OTHER_USERNAME"],
                "password": os.environ["TEST_OTHER_PASSWORD"],
            },
            timeout=10,
        )
        self.assertEqual(login.status_code, 200, login.text)

        other_headers = {
            "Authorization": f"Bearer {login.json()['access_token']}",
        }

        # 用当前测试账号创建专用任务
        created = self.client.post(
            f"{url}/tasks",
            json={"name": f"权限测试_{uuid4().hex}", "done": False},
            timeout=10,
        )
        self.assertEqual(created.status_code, 201, created.text)

        task_id = created.json()["id"]
        self.addCleanup(self.delete_test_task, task_id)

                # 检查另一个账号的所有分页，都看不到这条任务
        page = 1

        while True:
            response = self.client.get(
                f"{url}/tasks",
                headers=other_headers,
                params={"page": page, "size": 100},
                timeout=10,
            )
            self.assertEqual(response.status_code, 200, response.text)

            data = response.json()
            returned_ids = [task["id"] for task in data["items"]]
            self.assertNotIn(task_id, returned_ids)

            # 已检查最后一页，结束循环
            if page >= data["total_pages"]:
                break

            page += 1
            
        # 使用另一个账号的凭证尝试修改
        updated = self.client.patch(
            f"{url}/tasks/{task_id}",
            headers=other_headers,
            json={"done": True},
            timeout=10,
        )
        self.assertEqual(updated.status_code, 404, updated.text)

        # 使用另一个账号的凭证尝试删除
        deleted = self.client.delete(
            f"{url}/tasks/{task_id}",
            headers=other_headers,
            timeout=10,
        )
        self.assertEqual(deleted.status_code, 404, deleted.text)                                       