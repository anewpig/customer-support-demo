import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.repositories.sqlite_repository import SQLiteRepository
from app.services.chat_service import ChatService
from app.services.cleaning_service import FAQCleaningService


class FakeOpenAIService:
    def is_enabled(self):
        return False

    def get_runtime_status(self):
        return {
            "state": "disabled",
            "enabled": False,
            "quota_exhausted": False,
            "last_error_code": None,
            "last_error_message": None,
            "last_http_status": None,
            "last_success_at": None,
            "last_request_kind": None,
            "last_usage": {},
        }

    def generate_customer_reply(self, **_kwargs):
        return None

    def generate_staff_assistance(self, **_kwargs):
        return None


class FakeVectorStoreService:
    def __init__(self, vector_store_path):
        self.vector_store_path = vector_store_path

    def default_vector_store(self):
        return {"model": "text-embedding-3-small", "entries": [], "updated_at": None}

    def retrieve(self, _message, _faq_items, _vector_store):
        return [], "json"

    def get_chroma_collection(self):
        return None

    def has_usable_vector_index(self, _faq_items, _vector_store):
        return False

    def backend_name(self):
        return "json"

    def reindex_json(self, _faq_items):
        return {"count": 0, "model": "text-embedding-3-small", "backend": "json"}


class ChatServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.config = SimpleNamespace(
            faq_path=temp_path / "faq.json",
            orders_path=temp_path / "orders.json",
            conversations_path=temp_path / "conversations.json",
            sessions_path=temp_path / "sessions.json",
            vector_store_path=temp_path / "vector_store.json",
            openai_model="gpt-4.1-mini",
            embedding_model="text-embedding-3-small",
        )
        self.config.faq_path.write_text(
            """
            [
              {
                "id": "FAQ-1",
                "category": "refund",
                "question": "可以退款嗎？",
                "answer": "收到商品後 7 天內可申請退款。",
                "keywords": ["退款", "退貨"]
              }
            ]
            """,
            encoding="utf-8",
        )
        self.config.orders_path.write_text(
            """
            [
              {
                "order_id": "ORD-1001",
                "customer_name": "王小明",
                "customer_phone_last4": "4321",
                "status": "已成立",
                "shipping_status": "已出貨",
                "tracking_number": "TCAT88660001",
                "payment_status": "已付款",
                "invoice_type": "電子發票",
                "amount": 1280,
                "items": ["經典白T x1"]
              }
            ]
            """,
            encoding="utf-8",
        )
        self.cleaning_service = FAQCleaningService(self.config.faq_path)
        self.sqlite_repository = SQLiteRepository(temp_path / "app.db")
        self.vector_store_service = FakeVectorStoreService(self.config.vector_store_path)
        self.chat_service = ChatService(
            self.config,
            self.cleaning_service,
            FakeOpenAIService(),
            self.vector_store_service,
            self.sqlite_repository,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_compose_answer_saves_ticket_and_session(self):
        ticket = self.chat_service.compose_answer("我想申請退款", "session-1")

        self.assertEqual(ticket["intent"], "refund")
        self.assertIn("退款", ticket["response"])
        self.assertEqual(ticket["provider"], "local")

        conversations = self.sqlite_repository.list_conversations()
        session = self.sqlite_repository.get_session("session-1")

        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0]["id"], ticket["id"])
        self.assertEqual(session["last_ticket_id"], ticket["id"])

    def test_add_faq_updates_existing_question_in_same_category(self):
        updated = self.chat_service.add_faq(
            {
                "id": "FAQ-9",
                "category": "refund",
                "question": "可以退款嗎？",
                "answer": "新版退款說明。",
                "keywords": ["退款", "新版"],
            }
        )

        all_items = self.sqlite_repository.list_faq_items()
        refund_items = [item for item in all_items if item["category"] == "refund"]

        self.assertEqual(updated["answer"], "新版退款說明。")
        self.assertEqual(len(refund_items), 1)

    def test_order_lookup_uses_seeded_order_data(self):
        ticket = self.chat_service.compose_answer(
            "請幫我查 ORD-1001",
            "session-2",
            {"customer_phone_last4": "4321"},
        )

        self.assertEqual(ticket["intent"], "order_lookup")
        self.assertIn("ORD-1001", ticket["response"])
        self.assertIn("已出貨", ticket["response"])
        self.assertEqual(ticket["retrieval_method"], "order-db")

    def test_order_lookup_requires_verification_before_showing_details(self):
        ticket = self.chat_service.compose_answer("請幫我查 ORD-1001", "session-4")

        self.assertEqual(ticket["intent"], "order_lookup")
        self.assertIn("下單姓名或手機末四碼", ticket["response"])
        self.assertEqual(ticket["retrieval_method"], "order-db")

    def test_order_lookup_without_order_id_prompts_for_order_number(self):
        ticket = self.chat_service.compose_answer("幫我查訂單", "session-3")

        self.assertEqual(ticket["intent"], "order_lookup")
        self.assertEqual(ticket["retrieval_method"], "order-db")
        self.assertIn("訂單編號", ticket["response"])

    def test_get_ticket_assistance_returns_local_summary_and_reply(self):
        ticket = self.chat_service.compose_answer("我想申請退款", "session-5")
        assistance = self.chat_service.get_ticket_assistance(ticket["id"])

        self.assertEqual(assistance["ticket_id"], ticket["id"])
        self.assertEqual(assistance["provider"], "local")
        self.assertTrue(assistance["summary"])
        self.assertTrue(assistance["suggested_reply"])

    def test_get_status_normalizes_openai_runtime_when_key_is_enabled(self):
        class EnabledOpenAIService(FakeOpenAIService):
            def is_enabled(self):
                return True

        chat_service = ChatService(
            self.config,
            self.cleaning_service,
            EnabledOpenAIService(),
            self.vector_store_service,
            self.sqlite_repository,
        )

        status = chat_service.get_status()

        self.assertTrue(status["has_openai_key"])
        self.assertTrue(status["openai_runtime"]["enabled"])
        self.assertEqual(status["openai_runtime"]["state"], "idle")


if __name__ == "__main__":
    unittest.main()
