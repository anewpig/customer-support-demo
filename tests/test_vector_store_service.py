import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.repositories import json_repository
from app.services.vector_store_service import VectorStoreService


class FakeEmbeddingOpenAIService:
    def __init__(self):
        self.embedding_map = {
            "類別：refund\n問題：可以退款嗎？\n答案：收到商品後 7 天內可申請退款。\n關鍵字：退款 退貨": [1.0, 0.0],
            "類別：shipping\n問題：多久出貨？\n答案：付款後 24 小時內安排出貨。\n關鍵字：出貨 物流": [0.0, 1.0],
            "我要退款": [0.9, 0.1],
            "多久會出貨": [0.1, 0.95],
        }

    def is_enabled(self):
        return True

    def embed_texts(self, texts):
        return [{"embedding": self.embedding_map[text]} for text in texts]


class VectorStoreServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.config = SimpleNamespace(
            embedding_model="text-embedding-3-small",
            vector_store_path=temp_path / "vector_store.json",
            chroma_dir=temp_path / "chroma_db",
        )
        self.openai_service = FakeEmbeddingOpenAIService()
        self.service = VectorStoreService(self.config, self.openai_service, json_repository)
        self.faq_items = [
            {
                "id": "FAQ-1",
                "category": "refund",
                "question": "可以退款嗎？",
                "answer": "收到商品後 7 天內可申請退款。",
                "keywords": ["退款", "退貨"],
            },
            {
                "id": "FAQ-2",
                "category": "shipping",
                "question": "多久出貨？",
                "answer": "付款後 24 小時內安排出貨。",
                "keywords": ["出貨", "物流"],
            },
        ]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_reindex_json_creates_vector_store_entries(self):
        result = self.service.reindex_json(self.faq_items)

        self.assertEqual(result["backend"], "json")
        self.assertEqual(result["count"], 2)

        saved = json_repository.load_json(self.config.vector_store_path, {})
        self.assertEqual(len(saved["entries"]), 2)
        self.assertEqual(saved["entries"][0]["model"], "text-embedding-3-small")

    def test_retrieve_returns_most_similar_faq_for_refund_query(self):
        vector_store = {
            "model": "text-embedding-3-small",
            "entries": [
                {
                    "faq_id": "FAQ-1",
                    "document": self.service.faq_to_document(self.faq_items[0]),
                    "checksum": self.service.document_checksum(self.faq_items[0]),
                    "model": "text-embedding-3-small",
                    "embedding": [1.0, 0.0],
                },
                {
                    "faq_id": "FAQ-2",
                    "document": self.service.faq_to_document(self.faq_items[1]),
                    "checksum": self.service.document_checksum(self.faq_items[1]),
                    "model": "text-embedding-3-small",
                    "embedding": [0.0, 1.0],
                },
            ],
            "updated_at": None,
        }

        results, backend = self.service.retrieve("我要退款", self.faq_items, vector_store)

        self.assertIn(backend, {"json", "chroma"})
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "FAQ-1")

    def test_has_usable_vector_index_returns_true_for_current_entries(self):
        vector_store = {
            "model": "text-embedding-3-small",
            "entries": [
                {
                    "faq_id": "FAQ-1",
                    "document": self.service.faq_to_document(self.faq_items[0]),
                    "checksum": self.service.document_checksum(self.faq_items[0]),
                    "model": "text-embedding-3-small",
                    "embedding": [1.0, 0.0],
                }
            ],
            "updated_at": None,
        }

        usable = self.service.has_usable_vector_index([self.faq_items[0]], vector_store)

        self.assertTrue(usable)


if __name__ == "__main__":
    unittest.main()
