import json
import re
from datetime import datetime
from urllib import error, request


def utc_now():
    return datetime.now().isoformat(timespec="seconds")


class OpenAIService:
    def __init__(self, config):
        self.config = config
        self.runtime_status = {
            "state": "disabled" if not self.is_enabled() else "idle",
            "enabled": self.is_enabled(),
            "quota_exhausted": False,
            "last_error_code": None,
            "last_error_message": None,
            "last_http_status": None,
            "last_success_at": None,
            "last_request_kind": None,
            "last_usage": {},
        }

    def is_enabled(self):
        return bool(self.config.openai_api_key)

    def _record_success(self, payload, request_kind):
        usage = payload.get("usage", {}) if isinstance(payload, dict) else {}
        self.runtime_status.update(
            {
                "state": "ok",
                "enabled": True,
                "quota_exhausted": False,
                "last_error_code": None,
                "last_error_message": None,
                "last_http_status": 200,
                "last_success_at": utc_now(),
                "last_request_kind": request_kind,
                "last_usage": usage if isinstance(usage, dict) else {},
            }
        )

    def _record_error(self, *, message, error_code=None, http_status=None, request_kind=None):
        lowered_message = str(message or "").lower()
        quota_exhausted = (error_code or "") in {"insufficient_quota", "billing_hard_limit_reached"} or any(
            term in lowered_message for term in ("insufficient_quota", "billing", "credit", "quota")
        )
        self.runtime_status.update(
            {
                "state": "quota_exhausted" if quota_exhausted else "error",
                "enabled": self.is_enabled(),
                "quota_exhausted": quota_exhausted,
                "last_error_code": error_code or "unknown_error",
                "last_error_message": str(message),
                "last_http_status": http_status,
                "last_request_kind": request_kind,
            }
        )

    def _post(self, path, body, request_kind="generic"):
        req = request.Request(
            f"{self.config.openai_base_url}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.openai_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                self._record_success(payload, request_kind)
                return payload
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="ignore")
            error_code = None
            message = details
            try:
                parsed = json.loads(details)
                error_payload = parsed.get("error", {}) if isinstance(parsed, dict) else {}
                error_code = error_payload.get("code") or error_payload.get("type")
                message = error_payload.get("message") or details
            except json.JSONDecodeError:
                pass
            self._record_error(
                message=message,
                error_code=error_code,
                http_status=exc.code,
                request_kind=request_kind,
            )
            raise RuntimeError(f"OpenAI API error ({exc.code}): {message}") from exc
        except error.URLError as exc:
            message = f"OpenAI connection error: {exc.reason}"
            self._record_error(
                message=message,
                error_code="connection_error",
                http_status=None,
                request_kind=request_kind,
            )
            raise RuntimeError(message) from exc

    def get_runtime_status(self):
        return dict(self.runtime_status)

    def embed_texts(self, texts):
        if not self.is_enabled():
            raise RuntimeError("OPENAI_API_KEY is not set.")
        payload = self._post(
            "/embeddings",
            {
                "model": self.config.embedding_model,
                "input": texts,
                "encoding_format": "float",
            },
            request_kind="embeddings",
        )
        return payload.get("data", [])

    def generate_customer_reply(self, *, message, intent, results, escalate, session, history_context, rag_context, order_context, conversation_mode):
        if not self.is_enabled():
            return None
        if conversation_mode == "friendly_chat":
            instructions = (
                "你把使用者當成朋友一樣輕鬆的聊天。"
                "請用自然、口語、像朋友聊天的繁體中文回覆，不要像客服公告，也不要像機器人。"
                "除非對方主動把話題拉回訂單、退款、付款、發票或真人客服，否則不要提 FAQ、知識庫或轉人工。"
            )
        else:
            instructions = (
                "你是一位台灣電商品牌的客服人員，正在和顧客即時對話。"
                "請用自然、口語、溫和的繁體中文回答，像真人客服在聊天室裡回覆，不要像公告、聲明、新聞稿或機器人提示。"
                "直接回答問題就好，不要先講『您好』、『親愛的顧客』、『感謝您的理解與耐心』這類固定套話，除非語境真的需要。"
                "不要每次自我介紹，也不要主動說自己是 AI、客服助理或本品牌系統，除非使用者直接問你是誰。"
                "優先用一句到三句把重點講清楚；簡單問題就短答，避免冗長。"
                "只能根據提供的 FAQ 內容回答政策、流程、退款、出貨、付款等事實，不可捏造規則。"
                "如果 FAQ 不足以支持明確答案，不要硬編，也不要立刻官腔式轉人工；先自然地說目前手上資訊不夠，並請對方補充一點情況。"
                "只有在使用者明確要求真人客服、情緒強烈、或問題真的超出知識範圍時，才建議轉真人客服。"
                "多用像『我幫你查一下』、『看起來是可以的』、『如果是這種情況』這種真人客服會用的說法。"
            )
        prompt = (
            f"最新使用者問題：{message}\n"
            f"判定意圖：{intent}\n"
            f"對話模式：{conversation_mode}\n"
            f"是否建議轉人工：{'是' if escalate else '否'}\n\n"
            f"近期對話歷史：\n{history_context}\n\n"
            f"訂單資料：\n{order_context}\n\n"
            f"FAQ 內容：\n{rag_context}\n\n"
            "請直接輸出最終客服回覆。不要加標題，不要列點，不要寫成公文，不要重複自我介紹。"
        )
        body = {
            "model": self.config.openai_model,
            "instructions": instructions,
            "input": [{"role": "user", "content": prompt}],
            "max_output_tokens": 300,
        }
        previous_response_id = session.get("last_openai_response_id")
        if previous_response_id:
            body["previous_response_id"] = previous_response_id

        payload = self._post("/responses", body, request_kind="customer_reply")
        text = payload.get("output_text")
        if text:
            return {
                "text": text.strip(),
                "response_id": payload.get("id"),
                "usage": payload.get("usage", {}),
                "used_previous_response_id": previous_response_id,
            }

        for item in payload.get("output", []):
            if item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if content.get("type") == "output_text" and content.get("text"):
                    return {
                        "text": content["text"].strip(),
                        "response_id": payload.get("id"),
                        "usage": payload.get("usage", {}),
                        "used_previous_response_id": previous_response_id,
                    }

        raise RuntimeError("OpenAI API returned no text output.")

    def generate_staff_assistance(self, *, ticket, session_history, faq_context):
        if not self.is_enabled():
            return None
        instructions = (
            "你是客服主管助理，要幫真人客服快速接手案件。"
            "請用繁體中文，輸出簡潔、可直接工作的內容。"
            "請務必只輸出兩行："
            "第一行以 SUMMARY: 開頭，摘要案件重點。"
            "第二行以 SUGGESTED_REPLY: 開頭，產出一段可直接回覆顧客的建議文字。"
        )
        prompt = (
            f"工單編號：{ticket['id']}\n"
            f"問題類型：{ticket['intent']}\n"
            f"顧客訊息：{ticket['customer_message']}\n"
            f"AI 目前回覆：{ticket['response']}\n"
            f"Session 歷史：\n{session_history}\n\n"
            f"FAQ 內容：\n{faq_context}\n"
        )
        payload = self._post(
            "/responses",
            {
                "model": self.config.openai_model,
                "instructions": instructions,
                "input": [{"role": "user", "content": prompt}],
                "max_output_tokens": 220,
            },
            request_kind="staff_assistance",
        )
        text = payload.get("output_text", "").strip()
        if not text:
            for item in payload.get("output", []):
                if item.get("type") != "message":
                    continue
                for content in item.get("content", []):
                    if content.get("type") == "output_text" and content.get("text"):
                        text = content["text"].strip()
                        break
        if not text:
            raise RuntimeError("OpenAI staff assistance returned no text output.")

        summary_match = re.search(r"SUMMARY:\s*(.+)", text)
        reply_match = re.search(r"SUGGESTED_REPLY:\s*(.+)", text)
        return {
            "summary": summary_match.group(1).strip() if summary_match else "",
            "suggested_reply": reply_match.group(1).strip() if reply_match else "",
            "provider": "openai",
        }
