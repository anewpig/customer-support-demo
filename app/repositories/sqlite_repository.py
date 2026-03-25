import json
import sqlite3


class SQLiteRepository:
    def __init__(self, db_path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self):
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS faq_items (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    keywords_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    customer_message TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    response TEXT NOT NULL,
                    needs_handoff INTEGER NOT NULL,
                    citations_json TEXT NOT NULL,
                    trace_json TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    retrieval_method TEXT NOT NULL,
                    handoff_status TEXT NOT NULL DEFAULT 'none',
                    handoff_notes TEXT,
                    assigned_to TEXT,
                    openai_response_id TEXT,
                    previous_response_id TEXT,
                    usage_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    updated_at TEXT,
                    last_ticket_id TEXT,
                    last_openai_response_id TEXT,
                    customer_name TEXT,
                    customer_phone_last4 TEXT
                );

                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    customer_name TEXT NOT NULL,
                    customer_phone_last4 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    shipping_status TEXT NOT NULL,
                    tracking_number TEXT,
                    payment_status TEXT NOT NULL,
                    invoice_type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    items_json TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_faq_items_category_question
                ON faq_items (category, question);

                CREATE INDEX IF NOT EXISTS idx_conversations_session_created_at
                ON conversations (session_id, created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_conversations_handoff_created_at
                ON conversations (needs_handoff, created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_orders_order_id
                ON orders (order_id);

                CREATE INDEX IF NOT EXISTS idx_orders_customer_name
                ON orders (customer_name);

                CREATE INDEX IF NOT EXISTS idx_orders_phone_last4
                ON orders (customer_phone_last4);
                """
            )
            existing_conversation_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()
            }
            if "handoff_status" not in existing_conversation_columns:
                conn.execute("ALTER TABLE conversations ADD COLUMN handoff_status TEXT NOT NULL DEFAULT 'none'")
            if "handoff_notes" not in existing_conversation_columns:
                conn.execute("ALTER TABLE conversations ADD COLUMN handoff_notes TEXT")
            if "assigned_to" not in existing_conversation_columns:
                conn.execute("ALTER TABLE conversations ADD COLUMN assigned_to TEXT")

            existing_session_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()
            }
            if "customer_name" not in existing_session_columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN customer_name TEXT")
            if "customer_phone_last4" not in existing_session_columns:
                conn.execute("ALTER TABLE sessions ADD COLUMN customer_phone_last4 TEXT")

    def _serialize_keywords(self, keywords):
        return json.dumps(keywords or [], ensure_ascii=False)

    def _deserialize_faq_row(self, row):
        return {
            "id": row["id"],
            "category": row["category"],
            "question": row["question"],
            "answer": row["answer"],
            "keywords": json.loads(row["keywords_json"] or "[]"),
        }

    def _deserialize_conversation_row(self, row):
        return {
            "id": row["id"],
            "session_id": row["session_id"],
            "customer_message": row["customer_message"],
            "intent": row["intent"],
            "response": row["response"],
            "needs_handoff": bool(row["needs_handoff"]),
            "citations": json.loads(row["citations_json"] or "[]"),
            "trace": json.loads(row["trace_json"] or "[]"),
            "provider": row["provider"],
            "model": row["model"],
            "retrieval_method": row["retrieval_method"],
            "handoff_status": row["handoff_status"] or "none",
            "handoff_notes": row["handoff_notes"] or "",
            "assigned_to": row["assigned_to"] or "",
            "openai_response_id": row["openai_response_id"],
            "previous_response_id": row["previous_response_id"],
            "usage": json.loads(row["usage_json"] or "{}"),
            "created_at": row["created_at"],
        }

    def _deserialize_order_row(self, row):
        return {
            "order_id": row["order_id"],
            "customer_name": row["customer_name"],
            "customer_phone_last4": row["customer_phone_last4"],
            "status": row["status"],
            "shipping_status": row["shipping_status"],
            "tracking_number": row["tracking_number"],
            "payment_status": row["payment_status"],
            "invoice_type": row["invoice_type"],
            "amount": row["amount"],
            "items": json.loads(row["items_json"] or "[]"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def seed_faq_if_empty(self, faq_items):
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS count FROM faq_items").fetchone()["count"]
            if count > 0:
                return
            for item in faq_items:
                conn.execute(
                    """
                    INSERT INTO faq_items (id, category, question, answer, keywords_json)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (item["id"], item["category"], item["question"], item["answer"], self._serialize_keywords(item.get("keywords", []))),
                )

    def seed_orders_if_empty(self, orders):
        with self._connect() as conn:
            count = conn.execute("SELECT COUNT(*) AS count FROM orders").fetchone()["count"]
            if count > 0:
                return
            for order in orders:
                conn.execute(
                    """
                    INSERT INTO orders (
                        order_id, customer_name, customer_phone_last4, status, shipping_status,
                        tracking_number, payment_status, invoice_type, amount, items_json
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order["order_id"],
                        order["customer_name"],
                        order["customer_phone_last4"],
                        order["status"],
                        order["shipping_status"],
                        order.get("tracking_number"),
                        order["payment_status"],
                        order["invoice_type"],
                        order["amount"],
                        json.dumps(order.get("items", []), ensure_ascii=False),
                    ),
                )

    def list_faq_items(self):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM faq_items ORDER BY created_at DESC, id DESC").fetchall()
        return [self._deserialize_faq_row(row) for row in rows]

    def upsert_faq_item(self, item):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO faq_items (id, category, question, answer, keywords_json, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    category=excluded.category,
                    question=excluded.question,
                    answer=excluded.answer,
                    keywords_json=excluded.keywords_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (item["id"], item["category"], item["question"], item["answer"], self._serialize_keywords(item.get("keywords", []))),
            )

    def replace_faq_item_by_question(self, item):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM faq_items WHERE lower(question)=lower(?) AND category=? LIMIT 1",
                (item["question"], item["category"]),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE faq_items
                    SET id=?, answer=?, keywords_json=?, updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (item["id"], item["answer"], self._serialize_keywords(item.get("keywords", [])), row["id"]),
                )
                current = conn.execute("SELECT * FROM faq_items WHERE id=? LIMIT 1", (item["id"],)).fetchone()
                if current is None:
                    current = conn.execute("SELECT * FROM faq_items WHERE lower(question)=lower(?) AND category=? LIMIT 1", (item["question"], item["category"])).fetchone()
                return self._deserialize_faq_row(current) if current else item
        return None

    def save_conversation(self, ticket):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversations (
                    id, session_id, customer_message, intent, response, needs_handoff,
                    citations_json, trace_json, provider, model, retrieval_method,
                    handoff_status, handoff_notes, assigned_to,
                    openai_response_id, previous_response_id, usage_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket["id"],
                    ticket["session_id"],
                    ticket["customer_message"],
                    ticket["intent"],
                    ticket["response"],
                    int(ticket["needs_handoff"]),
                    json.dumps(ticket.get("citations", []), ensure_ascii=False),
                    json.dumps(ticket.get("trace", []), ensure_ascii=False),
                    ticket["provider"],
                    ticket["model"],
                    ticket["retrieval_method"],
                    ticket.get("handoff_status", "pending" if ticket["needs_handoff"] else "none"),
                    ticket.get("handoff_notes", ""),
                    ticket.get("assigned_to", ""),
                    ticket.get("openai_response_id"),
                    ticket.get("previous_response_id"),
                    json.dumps(ticket.get("usage", {}), ensure_ascii=False),
                    ticket["created_at"],
                ),
            )

    def list_conversations(self, *, needs_handoff=None):
        query = "SELECT * FROM conversations"
        params = []
        if needs_handoff is not None:
            query += " WHERE needs_handoff=?"
            params.append(int(needs_handoff))
        query += " ORDER BY created_at DESC, id DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._deserialize_conversation_row(row) for row in rows]

    def get_conversation(self, ticket_id):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE id=? LIMIT 1", (ticket_id,)).fetchone()
        return self._deserialize_conversation_row(row) if row else None

    def update_conversation_workflow(self, ticket_id, *, handoff_status, handoff_notes, assigned_to):
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE conversations
                SET handoff_status=?, handoff_notes=?, assigned_to=?
                WHERE id=?
                """,
                (handoff_status, handoff_notes, assigned_to, ticket_id),
            )
        return self.get_conversation(ticket_id)

    def list_recent_conversations_for_session(self, session_id, limit=3):
        return self._list_conversations_for_session(session_id, limit=limit)

    def list_conversations_for_session(self, session_id):
        return self._list_conversations_for_session(session_id)

    def _list_conversations_for_session(self, session_id, limit=None):
        query = """
            SELECT * FROM conversations
            WHERE session_id=?
            ORDER BY created_at DESC, id DESC
        """
        params = [session_id]
        if limit is not None:
            query += "\nLIMIT ?"
            params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._deserialize_conversation_row(row) for row in rows]

    def get_session(self, session_id):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE session_id=? LIMIT 1", (session_id,)).fetchone()
        if not row:
            return {}
        return {
            "updated_at": row["updated_at"],
            "last_ticket_id": row["last_ticket_id"],
            "last_openai_response_id": row["last_openai_response_id"],
            "customer_name": row["customer_name"] or "",
            "customer_phone_last4": row["customer_phone_last4"] or "",
        }

    def upsert_session(self, session_id, payload):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, updated_at, last_ticket_id, last_openai_response_id, customer_name, customer_phone_last4)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    updated_at=excluded.updated_at,
                    last_ticket_id=excluded.last_ticket_id,
                    last_openai_response_id=excluded.last_openai_response_id,
                    customer_name=excluded.customer_name,
                    customer_phone_last4=excluded.customer_phone_last4
                """,
                (
                    session_id,
                    payload.get("updated_at"),
                    payload.get("last_ticket_id"),
                    payload.get("last_openai_response_id"),
                    payload.get("customer_name"),
                    payload.get("customer_phone_last4"),
                ),
            )

    def get_order(self, order_id):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM orders WHERE order_id=? LIMIT 1", (order_id,)).fetchone()
        return self._deserialize_order_row(row) if row else None

    def list_orders(self, query=None):
        sql = "SELECT * FROM orders"
        params = []
        if query:
            sql += """
                WHERE order_id LIKE ? OR customer_name LIKE ? OR customer_phone_last4 LIKE ?
            """
            like_query = f"%{query}%"
            params.extend([like_query, like_query, like_query])
        sql += " ORDER BY created_at DESC, order_id DESC"
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._deserialize_order_row(row) for row in rows]
