import tempfile
import unittest
from pathlib import Path

from app.services.cleaning_service import FAQCleaningService


class FAQCleaningServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.faq_path = Path(self.temp_dir.name) / "faq.json"
        self.service = FAQCleaningService(self.faq_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_clean_item_normalizes_and_deduplicates_keywords(self):
        item = {
            "id": " FAQ-100 ",
            "category": " Shipping ",
            "question": "  請問   多久 出貨 ？ ",
            "answer": "  付款後  24 小時內 出貨 。 ",
            "keywords": ["出貨", " 出貨 ", "物流", "", "物流"],
        }

        cleaned = self.service.clean_item(item)

        self.assertEqual(cleaned["id"], "FAQ-100")
        self.assertEqual(cleaned["category"], "shipping")
        self.assertEqual(cleaned["question"], "請問 多久 出貨？")
        self.assertEqual(cleaned["answer"], "付款後 24 小時內 出貨。")
        self.assertEqual(cleaned["keywords"], ["出貨", "物流"])

    def test_clean_items_removes_invalid_and_duplicate_faqs(self):
        items = [
            {"id": "FAQ-1", "category": "refund", "question": "可以退款嗎？", "answer": "可以。", "keywords": ["退款"]},
            {"id": "FAQ-2", "category": "refund", "question": "可以退款嗎？", "answer": "可以。", "keywords": ["退款"]},
            {"id": "", "category": "refund", "question": "缺 id", "answer": "無效", "keywords": []},
        ]

        cleaned_items = self.service.clean_items(items)

        self.assertEqual(len(cleaned_items), 1)
        self.assertEqual(cleaned_items[0]["id"], "FAQ-1")


if __name__ == "__main__":
    unittest.main()
