import tempfile
import unittest
from pathlib import Path

from app.config import AppConfig
from app.database import Database
from app.services.content_service import ContentService


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_dir.name) / "test.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_product_account_task_flow(self):
        product_id = self.database.save_product(
            {
                "name": "测试商品",
                "main_image": "/tmp/test.jpg",
                "product_id": "SKU-001",
                "selling_points": "轻便耐用",
                "tags": "实用,好物",
            }
        )
        account_id = self.database.save_account(
            "测试账号",
            "/tmp/state.json",
        )
        task_id = self.database.create_task(
            {
                "product_id": product_id,
                "account_id": account_id,
                "title": "测试标题",
                "content": "测试正文",
                "tags": ["实用"],
                "images": ["/tmp/test.jpg"],
                "scheduled_at": None,
            }
        )

        task = self.database.get_task(task_id)
        self.assertEqual(task["product_name"], "测试商品")
        self.assertEqual(task["platform_product_id"], "SKU-001")
        self.assertEqual(task["status"], "pending")

        self.database.cancel_task(task_id)
        self.assertEqual(self.database.get_task(task_id)["status"], "cancelled")

        self.database.retry_task(task_id)
        self.assertEqual(self.database.get_task(task_id)["status"], "pending")


class ContentTests(unittest.TestCase):
    def test_offline_generation_returns_three_versions(self):
        service = ContentService(AppConfig(api_key=""))
        variants = service.generate_variants(
            {
                "name": "桌面收纳盒",
                "selling_points": "分区清楚，拿取方便",
                "tags": "收纳,桌面",
            }
        )
        self.assertEqual(len(variants), 3)
        self.assertEqual(
            [variant.style for variant in variants],
            ["种草", "测评", "促销"],
        )
        self.assertTrue(all(len(variant.title) <= 20 for variant in variants))


if __name__ == "__main__":
    unittest.main()
