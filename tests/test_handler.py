import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.repositories.sqlite_repository import SQLiteRepository
from app.services.auth_service import AuthService
from app.services.chat_service import ChatService
from app.services.cleaning_service import FAQCleaningService
from app.web.handler import create_app_handler


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


class HandlerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.config = SimpleNamespace(
            faq_path=temp_path / "faq.json",
            orders_path=temp_path / "orders.json",
            conversations_path=temp_path / "conversations.json",
            sessions_path=temp_path / "sessions.json",
            vector_store_path=temp_path / "vector_store.json",
            sqlite_path=temp_path / "app.db",
            static_dir=temp_path / "static",
            openai_model="gpt-4.1-mini",
            embedding_model="text-embedding-3-small",
            admin_username="admin",
            admin_password="password123",
            admin_cookie_name="supportos_admin_session",
        )
        self.config.static_dir.mkdir(parents=True, exist_ok=True)
        (self.config.static_dir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
        (self.config.static_dir / "admin.html").write_text("<html><body>admin</body></html>", encoding="utf-8")
        (self.config.static_dir / "login.html").write_text("<html><body>login</body></html>", encoding="utf-8")
        self.config.faq_path.write_text(
            json.dumps(
                [
                    {
                        "id": "FAQ-1",
                        "category": "refund",
                        "question": "可以退款嗎？",
                        "answer": "收到商品後 7 天內可申請退款。",
                        "keywords": ["退款", "退貨"],
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.config.orders_path.write_text(
            json.dumps(
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
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        cleaning_service = FAQCleaningService(self.config.faq_path)
        sqlite_repository = SQLiteRepository(self.config.sqlite_path)
        chat_service = ChatService(
            self.config,
            cleaning_service,
            FakeOpenAIService(),
            FakeVectorStoreService(self.config.vector_store_path),
            sqlite_repository,
        )
        self.auth_service = AuthService(self.config)
        self.handler_class = create_app_handler(chat_service, self.auth_service, self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def make_handler(self, method, path, payload=None, extra_headers=None):
        handler = self.handler_class.__new__(self.handler_class)
        body = b""
        headers = {}
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Length"] = str(len(body))
        else:
            headers["Content-Length"] = "0"
        headers.update(extra_headers or {})

        handler.path = path
        handler.headers = headers
        handler.rfile = io.BytesIO(body)
        handler.wfile = io.BytesIO()
        handler.command = method
        handler.request_version = "HTTP/1.1"
        handler.close_connection = True
        handler.response_code = None
        handler.response_headers = {}

        def send_response(code, _message=None):
            handler.response_code = code

        def send_header(key, value):
            handler.response_headers[key] = value

        def end_headers():
            return None

        def send_error(code, _message=None):
            handler.response_code = code

        handler.send_response = send_response
        handler.send_header = send_header
        handler.end_headers = end_headers
        handler.send_error = send_error
        return handler

    def read_json_response(self, handler):
        handler.wfile.seek(0)
        return json.loads(handler.wfile.read().decode("utf-8"))

    def test_healthz_endpoint(self):
        handler = self.make_handler("GET", "/healthz")
        handler.do_GET()

        payload = self.read_json_response(handler)
        self.assertEqual(handler.response_code, 200)
        self.assertTrue(payload["ok"])
        self.assertIn("timestamp", payload)

    def test_status_endpoint(self):
        handler = self.make_handler("GET", "/api/status")
        handler.do_GET()

        payload = self.read_json_response(handler)
        self.assertEqual(handler.response_code, 200)
        self.assertEqual(payload["provider"], "local")
        self.assertFalse(payload["has_openai_key"])
        self.assertIn("openai_runtime", payload)
        self.assertEqual(payload["openai_runtime"]["state"], "disabled")

    def test_chat_endpoint_returns_ticket(self):
        handler = self.make_handler("POST", "/api/chat", {"message": "我要退款", "session_id": "session-1"})
        handler.do_POST()

        payload = self.read_json_response(handler)
        self.assertEqual(handler.response_code, 200)
        self.assertEqual(payload["intent"], "refund")
        self.assertEqual(payload["provider"], "local")
        self.assertIn("response", payload)

    def test_chat_endpoint_can_lookup_order(self):
        handler = self.make_handler("POST", "/api/chat", {"message": "查一下 ORD-1001", "session_id": "session-2"})
        handler.do_POST()

        payload = self.read_json_response(handler)
        self.assertEqual(handler.response_code, 200)
        self.assertEqual(payload["intent"], "order_lookup")
        self.assertIn("ORD-1001", payload["response"])

    def test_admin_login_and_ai_assistance_endpoint(self):
        chat_handler = self.make_handler("POST", "/api/chat", {"message": "我要退款", "session_id": "session-3"})
        chat_handler.do_POST()
        ticket = self.read_json_response(chat_handler)

        login_handler = self.make_handler(
            "POST",
            "/api/admin/login",
            {"username": "admin", "password": "password123"},
        )
        login_handler.do_POST()
        login_payload = self.read_json_response(login_handler)
        cookie_header = login_handler.response_headers.get("Set-Cookie", "").split(";", 1)[0]

        self.assertEqual(login_handler.response_code, 200)
        self.assertTrue(login_payload["ok"])

        assistance_handler = self.make_handler(
            "GET",
            f"/api/tickets/assistance?ticket_id={ticket['id']}",
            extra_headers={"Cookie": cookie_header},
        )
        assistance_handler.do_GET()
        assistance_payload = self.read_json_response(assistance_handler)

        self.assertEqual(assistance_handler.response_code, 200)
        self.assertEqual(assistance_payload["ticket_id"], ticket["id"])
        self.assertIn("退款", assistance_payload["summary"])

    def test_orders_endpoint_requires_admin_auth(self):
        handler = self.make_handler("GET", "/api/orders")
        handler.do_GET()

        payload = self.read_json_response(handler)
        self.assertEqual(handler.response_code, 401)
        self.assertIn("authorization", payload["error"])

    def test_admin_login_can_fetch_orders(self):
        login_handler = self.make_handler(
            "POST",
            "/api/admin/login",
            {"username": "admin", "password": "password123"},
        )
        login_handler.do_POST()
        cookie_header = login_handler.response_headers.get("Set-Cookie", "").split(";", 1)[0]

        orders_handler = self.make_handler(
            "GET",
            "/api/orders?q=ORD-1001",
            extra_headers={"Cookie": cookie_header},
        )
        orders_handler.do_GET()
        payload = self.read_json_response(orders_handler)

        self.assertEqual(orders_handler.response_code, 200)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["order_id"], "ORD-1001")

    def test_admin_login_returns_invalid_username_error(self):
        handler = self.make_handler(
            "POST",
            "/api/admin/login",
            {"username": "wrong-user", "password": "password123"},
        )
        handler.do_POST()
        payload = self.read_json_response(handler)

        self.assertEqual(handler.response_code, 401)
        self.assertEqual(payload["error_code"], "invalid_username")

    def test_admin_login_returns_invalid_password_error(self):
        handler = self.make_handler(
            "POST",
            "/api/admin/login",
            {"username": "admin", "password": "wrong-password"},
        )
        handler.do_POST()
        payload = self.read_json_response(handler)

        self.assertEqual(handler.response_code, 401)
        self.assertEqual(payload["error_code"], "invalid_password")


if __name__ == "__main__":
    unittest.main()
