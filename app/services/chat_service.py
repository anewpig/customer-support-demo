import re
from collections import Counter
from datetime import datetime

from app.repositories.json_repository import load_json, save_json

ORDER_HINT_TERMS = ("訂單", "單號", "查單")
INTENT_KEYWORDS = {
    "refund": ("退款", "退貨", "cancel", "refund"),
    "shipping": ("運送", "物流", "出貨", "配送", "shipping"),
    "payment": ("付款", "刷卡", "發票", "payment"),
    "human_handoff": ("人工", "客服", "真人", "專員"),
}
ESCALATION_TERMS = ("客訴", "生氣", "投訴", "告你", "很糟", "爛", "人工", "真人")
SUPPORT_INTENTS = {"order_lookup", "refund", "shipping", "payment", "human_handoff"}
FAQ_CONTEXT_LIMIT = 2
DEFAULT_HISTORY_LIMIT = 3


def utc_now():
    return datetime.now().isoformat(timespec="seconds")


def tokenize(text):
    return re.findall(r"[\w\u4e00-\u9fff]+", text.lower())


def normalize_order_id(value):
    text = str(value or "").strip().upper().replace("_", "-").replace(" ", "")
    if re.fullmatch(r"ORD-\d{4}", text):
        return text
    if re.fullmatch(r"ORD\d{4}", text):
        return f"ORD-{text[-4:]}"
    return None


def normalize_phone_last4(value):
    digits = re.sub(r"\D+", "", str(value or ""))
    return digits[-4:] if len(digits) >= 4 else ""


def score_match(query, doc):
    query_tokens = tokenize(query)
    doc_tokens = tokenize(f"{doc['question']} {doc['answer']} {' '.join(doc.get('keywords', []))}")
    if not query_tokens or not doc_tokens:
        return 0

    query_counts = Counter(query_tokens)
    doc_counts = Counter(doc_tokens)
    overlap = sum(min(query_counts[token], doc_counts[token]) for token in query_counts)
    phrase_bonus = sum(2 for keyword in doc.get("keywords", []) if keyword.lower() in query.lower())
    category_bonus = 1 if doc.get("category", "").lower() in query.lower() else 0
    return overlap + phrase_bonus + category_bonus


def faq_identity_key(item):
    return (item["category"], item["question"].lower())


class ChatService:
    def __init__(self, config, cleaning_service, openai_service, vector_store_service, sqlite_repository):
        self.config = config
        self.cleaning_service = cleaning_service
        self.openai_service = openai_service
        self.vector_store_service = vector_store_service
        self.sqlite_repository = sqlite_repository
        self.faq_items = []
        self.faq_lookup = {}
        self.faq_by_identity = {}
        self.vector_store = {}
        self.reload()

    def reload(self):
        self._seed_initial_data()
        self._refresh_faq_cache()
        self._refresh_vector_store()

    def _seed_initial_data(self):
        cleaned_seed_items = self.cleaning_service.clean_items(load_json(self.config.faq_path, []))
        self.sqlite_repository.seed_faq_if_empty(cleaned_seed_items)
        self.sqlite_repository.seed_orders_if_empty(load_json(self.config.orders_path, []))

    def _refresh_faq_cache(self):
        self.faq_items = self.cleaning_service.clean_items(self.sqlite_repository.list_faq_items())
        self.faq_lookup = {item["id"]: item for item in self.faq_items}
        self.faq_by_identity = {faq_identity_key(item): item for item in self.faq_items}

    def _refresh_vector_store(self):
        self.vector_store = load_json(self.config.vector_store_path, self.vector_store_service.default_vector_store())

    def _invalidate_vector_store(self):
        self.vector_store["updated_at"] = None
        save_json(self.config.vector_store_path, self.vector_store)

    def _build_session_context(self, session_id, *, limit, empty_message):
        items = self.sqlite_repository.list_recent_conversations_for_session(session_id, limit=limit)
        if not items:
            return empty_message
        lines = []
        for item in reversed(items):
            lines.append(f"顧客：{item['customer_message']}")
            lines.append(f"客服：{item['response']}")
        return "\n".join(lines)

    def _response_from_mode(self, message, conversation_mode, results, escalate):
        if conversation_mode == "friendly_chat":
            return self.local_friendly_response(message)
        return self.local_response(results, escalate)

    def _build_citations(self, results, order):
        citations = [{"id": item["id"], "question": item["question"], "category": item["category"]} for item in results]
        if order:
            citations.insert(0, {"id": order["order_id"], "question": "訂單查詢結果", "category": "order"})
        return citations

    def _build_trace(self, *, session_id, intent, verification_state, conversation_mode, retrieval_method, results, provider, previous_response_id, llm_error, escalate):
        trace = [
            {"agent": "Session Agent", "output": f"session_id={session_id}"},
            {"agent": "Intent Agent", "output": f"判定問題類型：{intent}"},
            {
                "agent": "Verification Agent",
                "output": f"訂單驗證狀態：{verification_state}" if intent == "order_lookup" else "此輪不需訂單驗證",
            },
            {"agent": "Tone Agent", "output": f"使用 {conversation_mode} 模式"},
            {
                "agent": "Retriever Agent",
                "output": f"使用 {retrieval_method} retrieval，找到相關知識："
                + (", ".join(item["id"] for item in results) if results else "無高相似答案"),
            },
            {
                "agent": "Response Agent",
                "output": (
                    "直接使用訂單資料生成查詢結果"
                    if intent == "order_lookup"
                    else "使用 OpenAI 生成最終回覆，並串接先前對話狀態"
                    if provider == "openai" and previous_response_id
                    else "使用 OpenAI 生成最終回覆"
                    if provider == "openai"
                    else "使用本地 fallback 回覆"
                ),
            },
            {"agent": "Escalation Agent", "output": "建議轉人工客服" if escalate else "可由 AI 自助完成回覆"},
        ]
        if llm_error:
            trace.append({"agent": "LLM Fallback", "output": llm_error})
        return trace

    def _build_ticket(self, *, session_id, message, intent, response, needs_handoff, citations, trace, provider, retrieval_method, llm_response_id, previous_response_id, usage):
        return {
            "id": f"TICKET-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "session_id": session_id,
            "customer_message": message,
            "intent": intent,
            "response": response,
            "needs_handoff": needs_handoff,
            "citations": citations,
            "trace": trace,
            "provider": provider,
            "model": self.config.openai_model if provider == "openai" else "local-rules",
            "retrieval_method": retrieval_method,
            "handoff_status": "pending" if needs_handoff else "none",
            "handoff_notes": "",
            "assigned_to": "",
            "openai_response_id": llm_response_id,
            "previous_response_id": previous_response_id,
            "usage": usage,
            "created_at": utc_now(),
        }

    def _persist_session(self, session_id, session, ticket, customer_name, customer_phone_last4, llm_response_id):
        session["updated_at"] = ticket["created_at"]
        session["last_ticket_id"] = ticket["id"]
        if customer_name:
            session["customer_name"] = customer_name
        if customer_phone_last4:
            session["customer_phone_last4"] = customer_phone_last4
        if llm_response_id:
            session["last_openai_response_id"] = llm_response_id
        self.sqlite_repository.upsert_session(session_id, session)

    def classify_intent(self, message):
        lowered = message.lower()
        if self.extract_order_id(message) or any(term in lowered for term in ORDER_HINT_TERMS):
            return "order_lookup"
        for intent, keywords in INTENT_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                return intent
        return "friendly_chat"

    def keyword_retrieve(self, message):
        ranked = [(score_match(message, item), item) for item in self.faq_items]
        ranked = [pair for pair in ranked if pair[0] > 0]
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in ranked[:3]]

    def retrieve(self, message):
        try:
            if self.openai_service.is_enabled():
                vector_results, backend = self.vector_store_service.retrieve(message, self.faq_items, self.vector_store)
                if vector_results:
                    return vector_results, f"vector-{backend}"
        except RuntimeError:
            pass
        return self.keyword_retrieve(message), "keyword"

    def should_escalate(self, message, _results):
        lowered = message.lower()
        return any(term in lowered for term in ESCALATION_TERMS)

    def build_context(self, results):
        if not results:
            return "沒有找到可用 FAQ。"
        return "\n\n".join(
            f"[{item['id']}] 類別：{item['category']}\n問題：{item['question']}\n答案：{item['answer']}"
            for item in results[:FAQ_CONTEXT_LIMIT]
        )

    def build_history_context(self, session_id, limit=DEFAULT_HISTORY_LIMIT):
        return self._build_session_context(session_id, limit=limit, empty_message="這是這位使用者的第一輪對話。")

    def build_full_session_context(self, session_id, limit=8):
        return self._build_session_context(session_id, limit=limit, empty_message="沒有可用對話紀錄。")

    def extract_order_id(self, message):
        match = re.search(r"\bORD[-_ ]?\d{4}\b", str(message or ""), flags=re.IGNORECASE)
        return normalize_order_id(match.group(0)) if match else None

    def find_order(self, message):
        order_id = self.extract_order_id(message)
        return self.sqlite_repository.get_order(order_id) if order_id else None

    def order_verification_result(self, order, customer_name, customer_phone_last4):
        if not order:
            return "missing_order"

        normalized_name = str(customer_name or "").strip()
        normalized_phone_last4 = normalize_phone_last4(customer_phone_last4)
        name_matches = bool(normalized_name) and normalized_name == order["customer_name"]
        phone_matches = bool(normalized_phone_last4) and normalized_phone_last4 == order["customer_phone_last4"]
        if not normalized_name and not normalized_phone_last4:
            return "needs_verification"
        if name_matches or phone_matches:
            return "verified"
        return "verification_failed"

    def build_order_context(self, order):
        if not order:
            return "沒有找到可用訂單資料。"
        items = "、".join(order.get("items", [])) or "未提供"
        tracking_number = order.get("tracking_number") or "尚未產生"
        return (
            f"訂單編號：{order['order_id']}\n"
            f"收件人：{order['customer_name']}\n"
            f"手機末四碼：{order['customer_phone_last4']}\n"
            f"訂單狀態：{order['status']}\n"
            f"出貨狀態：{order['shipping_status']}\n"
            f"付款狀態：{order['payment_status']}\n"
            f"發票類型：{order['invoice_type']}\n"
            f"物流單號：{tracking_number}\n"
            f"商品內容：{items}\n"
            f"訂單金額：NT${int(order['amount'])}"
        )

    def local_response(self, results, escalate):
        response = results[0]["answer"] if results else "我目前手上的資料還不足以直接確認這個問題，你可以再多提供一點情況，我幫你接著查。"
        if escalate:
            response += "\n\n如果你希望直接由真人客服協助，我也可以幫你轉接。"
        return response

    def local_order_response(self, message, order, verification_state):
        if verification_state == "verified" and order:
            tracking_number = order.get("tracking_number") or "尚未產生"
            return (
                f"我幫你查到 {order['order_id']} 了，目前是「{order['status']}」，出貨狀態是「{order['shipping_status']}」。"
                f"付款狀態是「{order['payment_status']}」，物流單號是「{tracking_number}」。"
            )
        if verification_state == "needs_verification" and order:
            return (
                f"我有找到 {order['order_id']} 這筆訂單。"
                "為了保護訂單資料，請再提供下單姓名或手機末四碼，我就可以幫你顯示完整狀態。"
            )
        if verification_state == "verification_failed" and order:
            return "我有找到這筆訂單，但你提供的驗證資訊和訂單資料對不上。你可以再確認下單姓名或手機末四碼後重新查詢。"
        if self.extract_order_id(message):
            return "我有收到你的訂單編號，但目前查不到這筆資料。你可以再確認一次單號是不是輸入成像 ORD-1001 這種格式。"
        return "可以，請把訂單編號貼給我，我幫你查。你可以直接輸入像 ORD-1001、ORD-1002 這種格式。"

    def conversation_mode_for(self, intent, _results):
        return "support" if intent in SUPPORT_INTENTS else "friendly_chat"

    def local_friendly_response(self, message):
        lowered = message.lower()
        if any(word in lowered for word in ("你是誰", "你是誰啊", "你現在是誰")):
            return "你可以先把我當成線上陪聊兼客服小幫手，有問題都可以丟給我。"
        if any(word in lowered for word in ("怎麼看", "你覺得", "意見")):
            return "如果只是隨便聊聊，我會先看你想從哪個角度聊，丟我多一點背景我比較能接得住。"
        return "這題比較像在聊天，我可以陪你聊聊。你如果願意，也可以再說得具體一點。"

    def build_ticket_summary_local(self, ticket, session_items):
        customer_points = [item["customer_message"] for item in session_items[:2]]
        point_text = "；".join(customer_points) if customer_points else ticket["customer_message"]
        return f"顧客主要在詢問「{ticket['intent']}」相關問題，目前重點是：{point_text}"

    def build_suggested_reply_local(self, ticket):
        if ticket["intent"] == "refund":
            return "我這邊先幫你確認退款申請條件，如果商品狀態符合，我們會協助你進入退款流程。"
        if ticket["intent"] == "shipping":
            return "我幫你確認目前的出貨進度，如果物流資訊更新，我也可以再補給你。"
        if ticket["intent"] == "payment":
            return "我先幫你確認付款與發票狀態，若需要，我也可以再進一步核對訂單資訊。"
        if ticket["intent"] == "order_lookup":
            return "我這邊可以再幫你核對訂單資訊，方便的話請確認下單姓名或手機末四碼。"
        return "我先幫你整理目前狀況，接著由我這邊協助你把問題確認清楚。"

    def get_ticket_assistance(self, ticket_id):
        ticket = self.sqlite_repository.get_conversation(ticket_id)
        if not ticket:
            return None

        session_items = self.sqlite_repository.list_conversations_for_session(ticket["session_id"])
        faq_context_items = [
            self.faq_lookup[citation["id"]]
            for citation in ticket.get("citations", [])
            if str(citation.get("id", "")).startswith("FAQ-") and citation["id"] in self.faq_lookup
        ]
        summary = self.build_ticket_summary_local(ticket, session_items)
        suggested_reply = self.build_suggested_reply_local(ticket)
        provider = "local"

        try:
            llm_result = self.openai_service.generate_staff_assistance(
                ticket=ticket,
                session_history=self.build_full_session_context(ticket["session_id"]),
                faq_context=self.build_context(faq_context_items),
            )
            if llm_result:
                summary = llm_result.get("summary") or summary
                suggested_reply = llm_result.get("suggested_reply") or suggested_reply
                provider = llm_result.get("provider", "openai")
        except RuntimeError:
            pass

        return {
            "ticket_id": ticket_id,
            "summary": summary,
            "suggested_reply": suggested_reply,
            "provider": provider,
        }

    def compose_answer(self, message, session_id, customer_context=None):
        customer_context = customer_context or {}
        intent = self.classify_intent(message)
        session = self.sqlite_repository.get_session(session_id)
        customer_name = str(customer_context.get("customer_name") or session.get("customer_name") or "").strip()
        customer_phone_last4 = normalize_phone_last4(
            customer_context.get("customer_phone_last4") or session.get("customer_phone_last4") or ""
        )

        order = self.find_order(message) if intent == "order_lookup" else None
        verification_state = (
            self.order_verification_result(order, customer_name, customer_phone_last4)
            if intent == "order_lookup"
            else "not_applicable"
        )
        results, retrieval_method = ([], "order-db") if intent == "order_lookup" else self.retrieve(message)
        escalate = self.should_escalate(message, results)
        conversation_mode = self.conversation_mode_for(intent, results)
        citations = self._build_citations(results, order)

        provider = "local"
        llm_response_id = None
        previous_response_id = None
        usage = {}
        llm_error = None

        if intent == "order_lookup":
            response = self.local_order_response(message, order, verification_state)
        else:
            try:
                llm_result = self.openai_service.generate_customer_reply(
                    message=message,
                    intent=intent,
                    results=results,
                    escalate=escalate,
                    session=session,
                    history_context=self.build_history_context(session_id),
                    rag_context=self.build_context(results),
                    order_context=self.build_order_context(order),
                    conversation_mode=conversation_mode,
                )
                if llm_result:
                    response = llm_result["text"]
                    provider = "openai"
                    llm_response_id = llm_result.get("response_id")
                    previous_response_id = llm_result.get("used_previous_response_id")
                    usage = llm_result.get("usage", {})
                else:
                    response = self._response_from_mode(message, conversation_mode, results, escalate)
            except RuntimeError as exc:
                llm_error = str(exc)
                response = self._response_from_mode(message, conversation_mode, results, escalate)

        trace = self._build_trace(
            session_id=session_id,
            intent=intent,
            verification_state=verification_state,
            conversation_mode=conversation_mode,
            retrieval_method=retrieval_method,
            results=results,
            provider=provider,
            previous_response_id=previous_response_id,
            llm_error=llm_error,
            escalate=escalate,
        )
        ticket = self._build_ticket(
            session_id=session_id,
            message=message,
            intent=intent,
            response=response,
            needs_handoff=escalate,
            citations=citations,
            trace=trace,
            provider=provider,
            retrieval_method=retrieval_method,
            llm_response_id=llm_response_id,
            previous_response_id=previous_response_id,
            usage=usage,
        )

        self._persist_session(session_id, session, ticket, customer_name, customer_phone_last4, llm_response_id)
        self.sqlite_repository.save_conversation(ticket)
        return ticket

    def get_conversations(self, *, needs_handoff=None, session_id=None):
        if session_id:
            items = self.sqlite_repository.list_conversations_for_session(session_id)
            if needs_handoff is not None:
                items = [item for item in items if item["needs_handoff"] == needs_handoff]
            return items
        return self.sqlite_repository.list_conversations(needs_handoff=needs_handoff)

    def update_workflow(self, ticket_id, *, handoff_status, handoff_notes, assigned_to):
        return self.sqlite_repository.update_conversation_workflow(
            ticket_id,
            handoff_status=handoff_status,
            handoff_notes=handoff_notes,
            assigned_to=assigned_to,
        )

    def list_orders(self, query=None):
        return self.sqlite_repository.list_orders(query=query)

    def get_faq_gap_analysis(self, limit=5):
        items = self.sqlite_repository.list_conversations()
        gaps = {}
        for item in items:
            if item["intent"] in {"friendly_chat", "order_lookup"}:
                continue
            has_faq_citation = any(str(citation.get("id", "")).startswith("FAQ-") for citation in item.get("citations", []))
            if has_faq_citation and not item["needs_handoff"]:
                continue
            normalized = re.sub(r"\s+", " ", re.sub(r"[^\w\u4e00-\u9fff]+", " ", item["customer_message"].lower())).strip()
            if not normalized:
                continue
            bucket = gaps.setdefault(
                normalized,
                {
                    "topic": item["customer_message"][:40],
                    "count": 0,
                    "latest_message": item["customer_message"],
                    "intent": item["intent"],
                    "reason": "需要人工介入" if item["needs_handoff"] else "FAQ 命中不足",
                },
            )
            bucket["count"] += 1
        return sorted(gaps.values(), key=lambda value: value["count"], reverse=True)[:limit]

    def add_faq(self, payload):
        faq_item = self.cleaning_service.clean_item(payload)
        duplicate = self.faq_by_identity.get(faq_identity_key(faq_item))
        if duplicate:
            saved = self.sqlite_repository.replace_faq_item_by_question(faq_item)
            self._refresh_faq_cache()
            self._invalidate_vector_store()
            return saved or self.faq_by_identity.get(faq_identity_key(faq_item))

        self.sqlite_repository.upsert_faq_item(faq_item)
        self._refresh_faq_cache()
        self._invalidate_vector_store()
        return faq_item

    def get_status(self):
        ready_state_getter = getattr(self.vector_store_service, "get_last_ready_state", None)
        ready_state = ready_state_getter() if callable(ready_state_getter) else {}
        collection = self.vector_store_service.get_chroma_collection()
        vector_entries = collection.count() if collection is not None else len(self.vector_store.get("entries", []))
        openai_enabled = self.openai_service.is_enabled()
        openai_runtime = self.openai_service.get_runtime_status() if hasattr(self.openai_service, "get_runtime_status") else {}
        if not isinstance(openai_runtime, dict):
            openai_runtime = {}
        openai_runtime = {
            **openai_runtime,
            "enabled": openai_enabled,
        }
        if openai_enabled and openai_runtime.get("state") == "disabled":
            openai_runtime["state"] = "idle"
        return {
            "provider": "openai" if openai_enabled else "local",
            "model": self.config.openai_model if openai_enabled else "local-rules",
            "has_openai_key": openai_enabled,
            "embedding_model": self.config.embedding_model,
            "vector_index_ready": self.vector_store_service.has_usable_vector_index(self.faq_items, self.vector_store),
            "vector_entries": vector_entries,
            "vector_backend": self.vector_store_service.backend_name(),
            "has_chroma": self.vector_store_service.backend_name() == "chroma",
            "vector_status_reason": ready_state.get("reason"),
            "vector_status_error": ready_state.get("error"),
            "openai_runtime": openai_runtime,
        }

    def reindex(self):
        self._refresh_faq_cache()
        result = (
            self.vector_store_service.reindex_chroma(self.faq_items)
            if self.vector_store_service.backend_name() == "chroma"
            else self.vector_store_service.reindex_json(self.faq_items)
        )
        self._refresh_vector_store()
        return result
