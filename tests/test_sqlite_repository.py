import tempfile
import unittest
from pathlib import Path

from app.repositories.sqlite_repository import SQLiteRepository


class SQLiteRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "app.db"
        self.repository = SQLiteRepository(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_seed_and_list_faq_items(self):
        self.repository.seed_faq_if_empty(
            [
                {
                    "id": "FAQ-1",
                    "category": "refund",
                    "question": "可以退款嗎？",
                    "answer": "可以。",
                    "keywords": ["退款"],
                }
            ]
        )

        items = self.repository.list_faq_items()

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], "FAQ-1")
        self.assertEqual(items[0]["keywords"], ["退款"])

    def test_save_conversation_and_session(self):
        ticket = {
            "id": "TICKET-1",
            "session_id": "session-1",
            "customer_message": "我要退款",
            "intent": "refund",
            "response": "可以申請退款。",
            "needs_handoff": False,
            "citations": [{"id": "FAQ-1"}],
            "trace": [{"agent": "Intent Agent", "output": "refund"}],
            "provider": "local",
            "model": "local-rules",
            "retrieval_method": "keyword",
            "openai_response_id": None,
            "previous_response_id": None,
            "usage": {},
            "created_at": "2026-03-25T21:00:00",
        }

        self.repository.save_conversation(ticket)
        self.repository.upsert_session(
            "session-1",
            {
                "updated_at": "2026-03-25T21:00:00",
                "last_ticket_id": "TICKET-1",
                "last_openai_response_id": None,
            },
        )

        conversations = self.repository.list_conversations()
        session = self.repository.get_session("session-1")

        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0]["customer_message"], "我要退款")
        self.assertEqual(session["last_ticket_id"], "TICKET-1")

    def test_seed_and_get_order(self):
        self.repository.seed_orders_if_empty(
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
                    "items": ["經典白T x1"],
                }
            ]
        )

        order = self.repository.get_order("ORD-1001")

        self.assertIsNotNone(order)
        self.assertEqual(order["customer_name"], "王小明")
        self.assertEqual(order["items"], ["經典白T x1"])


if __name__ == "__main__":
    unittest.main()
