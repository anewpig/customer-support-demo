import json
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, quote, urlparse

from app.services.chat_service import utc_now


def create_app_handler(chat_service, auth_service, config):
    static_cache = {}
    content_types = {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
    }

    class AppHandler(BaseHTTPRequestHandler):
        def _send_json(self, payload, status=200, extra_headers=None):
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            for key, value in (extra_headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

        def _send_redirect(self, location, extra_headers=None):
            self.send_response(302)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            for key, value in (extra_headers or {}).items():
                self.send_header(key, value)
            self.end_headers()

        def _send_file(self, path, extra_headers=None):
            if not path.exists() or not path.is_file():
                self.send_error(404, "Not found")
                return
            stat = path.stat()
            cache_key = str(path)
            cached = static_cache.get(cache_key)
            if cached and cached["mtime_ns"] == stat.st_mtime_ns:
                data = cached["data"]
            else:
                data = path.read_bytes()
                static_cache[cache_key] = {"mtime_ns": stat.st_mtime_ns, "data": data}
            content_type = content_types.get(path.suffix, "text/plain; charset=utf-8")
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            for key, value in (extra_headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)

        def _read_json_payload(self):
            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length) if length else b"{}"
            if not raw_body:
                return {}
            return json.loads(raw_body.decode("utf-8"))

        def _cookie_token(self):
            jar = SimpleCookie()
            raw_cookie = self.headers.get("Cookie", "")
            if raw_cookie:
                jar.load(raw_cookie)
            cookie = jar.get(config.admin_cookie_name)
            return cookie.value if cookie else None

        def _admin_session(self):
            return auth_service.get_session(self._cookie_token())

        def _is_admin_authorized(self):
            return auth_service.is_authorized(self._cookie_token())

        def _require_admin_api(self):
            if self._is_admin_authorized():
                return True
            self._send_json({"error": "admin authorization required"}, status=401)
            return False

        def _set_admin_cookie_headers(self, token=None, clear=False):
            if clear:
                cookie_value = (
                    f"{config.admin_cookie_name}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
                )
            else:
                cookie_value = (
                    f"{config.admin_cookie_name}={token}; Path=/; HttpOnly; SameSite=Lax"
                )
            return {"Set-Cookie": cookie_value}

        def do_GET(self):
            parsed = urlparse(self.path)

            if parsed.path == "/healthz":
                self._send_json({"ok": True, "timestamp": utc_now()})
                return

            if parsed.path == "/api/status":
                self._send_json(chat_service.get_status())
                return

            if parsed.path == "/api/admin/session":
                session = self._admin_session()
                self._send_json(
                    {
                        "authenticated": bool(session),
                        "username": session.get("username", "") if session else "",
                    }
                )
                return

            if parsed.path == "/api/faq":
                if not self._require_admin_api():
                    return
                self._send_json({"items": chat_service.faq_items})
                return

            if parsed.path == "/api/conversations":
                if not self._require_admin_api():
                    return
                params = parse_qs(parsed.query)
                needs_handoff = params.get("needs_handoff", [""])[0]
                session_id = params.get("session_id", [""])[0] or None
                items = chat_service.get_conversations(
                    needs_handoff=True if needs_handoff == "true" else None,
                    session_id=session_id,
                )
                self._send_json({"items": items})
                return

            if parsed.path == "/api/orders":
                if not self._require_admin_api():
                    return
                params = parse_qs(parsed.query)
                query = params.get("q", [""])[0] or None
                self._send_json({"items": chat_service.list_orders(query=query)})
                return

            if parsed.path == "/api/analysis/faq-gaps":
                if not self._require_admin_api():
                    return
                params = parse_qs(parsed.query)
                try:
                    limit = int(params.get("limit", ["5"])[0])
                except ValueError:
                    limit = 5
                self._send_json({"items": chat_service.get_faq_gap_analysis(limit=limit)})
                return

            if parsed.path == "/api/tickets/assistance":
                if not self._require_admin_api():
                    return
                params = parse_qs(parsed.query)
                ticket_id = params.get("ticket_id", [""])[0]
                if not ticket_id:
                    self._send_json({"error": "ticket_id is required"}, status=400)
                    return
                payload = chat_service.get_ticket_assistance(ticket_id)
                if not payload:
                    self._send_json({"error": "ticket not found"}, status=404)
                    return
                self._send_json(payload)
                return

            if parsed.path == "/admin.html" and not self._is_admin_authorized():
                next_target = quote(parsed.path, safe="/")
                self._send_redirect(f"/login.html?next={next_target}")
                return

            if parsed.path == "/login.html" and self._is_admin_authorized():
                self._send_redirect("/admin.html")
                return

            target = config.static_dir / ("index.html" if parsed.path == "/" else parsed.path.lstrip("/"))
            self._send_file(target)

        def do_POST(self):
            parsed = urlparse(self.path)
            payload = self._read_json_payload()

            if parsed.path == "/api/admin/login":
                username = str(payload.get("username", "")).strip()
                password = str(payload.get("password", "")).strip()
                if not username or not password:
                    self._send_json({"error": "username and password are required"}, status=400)
                    return
                login_result = auth_service.login(username, password)
                if not login_result.get("ok"):
                    self._send_json(
                        {
                            "error": login_result.get("message", "登入失敗"),
                            "error_code": login_result.get("error_code", "login_failed"),
                        },
                        status=401,
                    )
                    return
                self._send_json(
                    {"ok": True, "username": login_result["username"]},
                    extra_headers=self._set_admin_cookie_headers(token=login_result["token"]),
                )
                return

            if parsed.path == "/api/admin/logout":
                auth_service.logout(self._cookie_token())
                self._send_json({"ok": True}, extra_headers=self._set_admin_cookie_headers(clear=True))
                return

            if parsed.path == "/api/chat":
                if not payload.get("message"):
                    self._send_json({"error": "message is required"}, status=400)
                    return
                session_id = payload.get("session_id") or "default-session"
                self._send_json(
                    chat_service.compose_answer(
                        payload["message"],
                        session_id,
                        {
                            "customer_name": payload.get("customer_name", ""),
                            "customer_phone_last4": payload.get("customer_phone_last4", ""),
                        },
                    )
                )
                return

            if parsed.path == "/api/conversations/workflow":
                if not self._require_admin_api():
                    return
                required_fields = ["ticket_id", "handoff_status"]
                missing = [field for field in required_fields if not payload.get(field)]
                if missing:
                    self._send_json({"error": f"missing fields: {', '.join(missing)}"}, status=400)
                    return
                updated = chat_service.update_workflow(
                    payload["ticket_id"],
                    handoff_status=payload["handoff_status"],
                    handoff_notes=payload.get("handoff_notes", ""),
                    assigned_to=payload.get("assigned_to", ""),
                )
                if not updated:
                    self._send_json({"error": "ticket not found"}, status=404)
                    return
                self._send_json(updated, status=200)
                return

            if parsed.path == "/api/faq":
                if not self._require_admin_api():
                    return
                required_fields = ["id", "category", "question", "answer"]
                missing = [field for field in required_fields if not payload.get(field)]
                if missing:
                    self._send_json({"error": f"missing fields: {', '.join(missing)}"}, status=400)
                    return
                payload["keywords"] = [item.strip() for item in payload.get("keywords", []) if item.strip()]
                self._send_json(chat_service.add_faq(payload), status=201)
                return

            if parsed.path == "/api/reindex":
                if not self._require_admin_api():
                    return
                try:
                    self._send_json({"ok": True, **chat_service.reindex()}, status=201)
                except RuntimeError as exc:
                    self._send_json({"error": str(exc)}, status=400)
                return

            self._send_json({"error": "not found"}, status=404)

    return AppHandler
