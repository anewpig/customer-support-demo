import json
import re
from datetime import datetime
from urllib import error, request

#取得現在時間，並回傳 ISO 格式字串。
#主要拿來記錄「最後一次成功呼叫 API 的時間」。

def utc_now():
    return datetime.now().isoformat(timespec="seconds")


class OpenAIService:
    def __init__(self, config):
        #建立服務物件，存下設定。
        #同時初始化 runtime_status，用來追蹤 API 現在是否可用、上次成功或失敗狀態、錯誤訊息、token usage 等。
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

    #檢查 OpenAI 功能有沒有啟用。
    #本質上就是看 OPENAI_API_KEY 有沒有設定。
    def is_enabled(self):
        return bool(self.config.openai_api_key)

    #當 API 呼叫成功時，更新執行狀態。
    #會記錄成功時間、請求類型、HTTP 狀態、以及 usage 資訊。
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
    #當 API 呼叫失敗時，更新錯誤狀態。
    #也會判斷這是不是額度不足、帳務限制那類錯誤。
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

    #這是核心的「送出 POST 請求到 OpenAI API」方法。
    #它會組 request、送出 JSON、解析回應。
    #如果成功，就呼叫 _record_success。
    #如果 HTTP 錯誤或網路錯誤，就解析錯誤內容、呼叫 _record_error，再丟出 RuntimeError。
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

    #取得目前 API 執行狀態的副本。
    #給外部查看現在是正常、停用、錯誤還是額度耗盡。
    def get_runtime_status(self):
        return dict(self.runtime_status)

    #把一批文字送去 /embeddings，取得向量 embedding。
    #給 RAG / FAQ 相似度搜尋使用。
    #如果沒設定 API key，會直接報錯。
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

    #產生「給顧客看的最終回覆」。
    #它會根據使用者訊息、意圖判定、FAQ 檢索內容、訂單資訊、歷史對話、是否要轉人工、對話模式，組出 prompt 並呼叫 OpenAI。
    #如果 conversation_mode == "friendly_chat"，語氣會更像朋友聊天。
    #否則會用比較像真人客服的語氣。
    #如果 session 裡有上一輪的 response_id，也會帶上去，讓上下文更連續。
    #最後會從 API 回應裡把文字抽出來回傳。
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

    #產生「給真人客服接手用」的輔助內容。
    #輸出重點是兩部分：
    #案件摘要 summary
    #建議直接回覆顧客的文字 suggested_reply
    #它會把工單、session 歷史、FAQ 內容送給模型，要求模型用固定格式回傳，再用 regex 解析出兩段內容。
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
