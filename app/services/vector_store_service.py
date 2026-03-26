import json
import math

try:
    import chromadb
except ImportError:
    chromadb = None

#把一個大列表切成一小批一小批。
#是為了分批呼叫 embedding API，避免一次送太多資料。
def chunked(items, size): 
    for index in range(0, len(items), size):
        yield items[index:index + size]

#計算兩個向量的「餘弦相似度」。
#分數越高，代表兩段文字語意越接近。
#如果其中一個向量是空的或全 0，就直接回傳 0.0。
def cosine_similarity(left, right):
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    dot_product = sum(l_val * r_val for l_val, r_val in zip(left, right))
    return dot_product / (left_norm * right_norm)

#建立這個服務物件。
#接收設定、OpenAI 服務、JSON 儲存服務。
#同時初始化 Chroma collection 快取，以及一份目前索引狀態 last_ready_state
class VectorStoreService:
    def __init__(self, config, openai_service, json_repository):
        self.config = config
        self.openai_service = openai_service
        self.json_repository = json_repository
        self._chroma_collection = None
        self.last_ready_state = {
            "ready": False,
            "backend": self.backend_name(),
            "reason": "not_checked",
            "count": 0,
            "error": None,
        }

    #回傳一個「空的向量資料結構」預設值。
    #用在還沒建立索引時，先有一個基本格式
    def default_vector_store(self):
        return {"model": self.config.embedding_model, "entries": [], "updated_at": None}

    #取得 Chroma 的 collection。
    #如果沒裝 chromadb，就回傳 None。
    #如果有裝，會建立或打開本地持久化的 collection，並快取起來重複使用。
    def get_chroma_collection(self):
        if chromadb is None:
            return None
        if self._chroma_collection is not None:
            return self._chroma_collection
        self.config.chroma_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(self.config.chroma_dir))
        self._chroma_collection = client.get_or_create_collection(name="faq_knowledge_base")
        return self._chroma_collection

    #把一筆 FAQ 資料整理成一段可拿去做 embedding 的文字。
    #會把類別、問題、答案、關鍵字合併成一份 document。
    def faq_to_document(self, item):
        keyword_text = " ".join(item.get("keywords", []))
        return f"類別：{item['category']}\n問題：{item['question']}\n答案：{item['answer']}\n關鍵字：{keyword_text}".strip()

    #把 FAQ 內容整理成一個穩定的字串，用來判斷 FAQ 有沒有變動。
    def document_checksum(self, item):
        payload = {
            "category": item["category"],
            "question": item["question"],
            "answer": item["answer"],
            "keywords": item.get("keywords", []),
        }
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    #在 JSON 型的向量資料裡，找某個 FAQ 對應的 embedding 紀錄。
    def find_vector_entry(self, vector_store, faq_id):
        for entry in vector_store.get("entries", []):
            if entry["faq_id"] == faq_id:
                return entry
        return None

    #檢查 Chroma 索引是否可用。
    def has_usable_chroma_index(self):
        collection = self.get_chroma_collection()
        if collection is None:
            return False
        try:
            return collection.count() > 0
        except Exception:
            return False

    #檢查整體向量索引是否可用。
    #優先看 Chroma；如果沒有，就檢查 JSON 裡的 entries。
    #檢查重點包含：FAQ 是否有對應 embedding、內容是否沒過期、模型是否一致、embedding 是否存在。 
    def has_usable_vector_index(self, faq_items, vector_store):
        if self.has_usable_chroma_index():
            return True
        entries = vector_store.get("entries", [])
        if not entries:
            return False

        valid_entries = 0
        for item in faq_items:
            entry = self.find_vector_entry(vector_store, item["id"])
            if not entry:
                continue
            if entry.get("checksum") != self.document_checksum(item):
                continue
            if entry.get("model") != self.config.embedding_model:
                continue
            if not entry.get("embedding"):
                continue
            valid_entries += 1
        return valid_entries > 0

    #用 JSON 方式重建整份 FAQ 的 embedding 索引。
    #流程是：把 FAQ 轉文件 → 分批送去做 embedding → 存回 JSON。
    #成功後更新 last_ready_state。
    def reindex_json(self, faq_items):
        if not self.openai_service.is_enabled():
            raise RuntimeError("OPENAI_API_KEY is not set.")
        entries = []
        documents = [
            {"faq_id": item["id"], "document": self.faq_to_document(item), "checksum": self.document_checksum(item)}
            for item in faq_items
        ]
        for group in chunked(documents, 16):
            embeddings = self.openai_service.embed_texts([doc["document"] for doc in group])
            for doc, embedding_item in zip(group, embeddings):
                entries.append(
                    {
                        "faq_id": doc["faq_id"],
                        "document": doc["document"],
                        "checksum": doc["checksum"],
                        "model": self.config.embedding_model,
                        "embedding": embedding_item["embedding"],
                    }
                )
        vector_store = {"model": self.config.embedding_model, "entries": entries, "updated_at": None}
        self.json_repository.save_json(self.config.vector_store_path, vector_store)
        self.last_ready_state = {
            "ready": True,
            "backend": "json",
            "reason": "reindexed",
            "count": len(entries),
            "error": None,
        }
        return {"count": len(entries), "model": self.config.embedding_model, "backend": "json"}

    #用 Chroma 方式重建整份 FAQ 的索引。
    #如果 collection 裡本來有資料，先清掉，再整批重建。
    #每筆 FAQ 會存 document、metadata、embedding。
    #成功後更新 last_ready_state。
    def reindex_chroma(self, faq_items):
        if not self.openai_service.is_enabled():
            raise RuntimeError("OPENAI_API_KEY is not set.")
        collection = self.get_chroma_collection()
        if collection is None:
            raise RuntimeError("chromadb is not installed.")
        if collection.count() > 0:
            existing = collection.get(include=[])
            existing_ids = existing.get("ids", [])
            if existing_ids:
                collection.delete(ids=existing_ids)

        documents = [
            {
                "faq_id": item["id"],
                "document": self.faq_to_document(item),
                "metadata": {
                    "faq_id": item["id"],
                    "category": item["category"],
                    "question": item["question"],
                    "checksum": self.document_checksum(item),
                    "embedding_model": self.config.embedding_model,
                },
            }
            for item in faq_items
        ]
        for group in chunked(documents, 16):
            embeddings = self.openai_service.embed_texts([doc["document"] for doc in group])
            collection.add(
                ids=[doc["faq_id"] for doc in group],
                documents=[doc["document"] for doc in group],
                metadatas=[doc["metadata"] for doc in group],
                embeddings=[item["embedding"] for item in embeddings],
            )
        self.last_ready_state = {
            "ready": True,
            "backend": "chroma",
            "reason": "reindexed",
            "count": len(documents),
            "error": None,
        }
        return {"count": len(documents), "model": self.config.embedding_model, "backend": "chroma"}

    #確保索引已經準備好。
    #如果沒有 OpenAI key，就標記成 not ready。
    #如果有 Chroma，就優先檢查或重建 Chroma。
    #如果沒有 Chroma，就檢查 JSON 索引是否還是最新，不是的話就重建。
    #這個 function 很像「索引總管」。
    def ensure_vector_index(self, faq_items, vector_store):
        if not self.openai_service.is_enabled():
            self.last_ready_state = {
                "ready": False,
                "backend": self.backend_name(),
                "reason": "missing_openai_key",
                "count": 0,
                "error": None,
            }
            return self.last_ready_state
        try:
            if chromadb is not None:
                collection = self.get_chroma_collection()
                if collection is not None:
                    try:
                        count = collection.count()
                    except Exception:
                        count = 0
                    if count == len(faq_items) and count > 0:
                        self.last_ready_state = {
                            "ready": True,
                            "backend": "chroma",
                            "reason": "already_indexed",
                            "count": count,
                            "error": None,
                        }
                        return self.last_ready_state
                    result = self.reindex_chroma(faq_items)
                    self.last_ready_state = {
                        "ready": True,
                        "backend": "chroma",
                        "reason": "reindexed",
                        "count": result["count"],
                        "error": None,
                    }
                    return self.last_ready_state

            all_current = True
            for item in faq_items:
                entry = self.find_vector_entry(vector_store, item["id"])
                if not entry or entry.get("checksum") != self.document_checksum(item) or entry.get("model") != self.config.embedding_model:
                    all_current = False
                    break
            if all_current and vector_store.get("entries"):
                self.last_ready_state = {
                    "ready": True,
                    "backend": "json",
                    "reason": "already_indexed",
                    "count": len(vector_store.get("entries", [])),
                    "error": None,
                }
                return self.last_ready_state

            result = self.reindex_json(faq_items)
            self.last_ready_state = {
                "ready": True,
                "backend": "json",
                "reason": "reindexed",
                "count": result["count"],
                "error": None,
            }
            return self.last_ready_state
        except RuntimeError as exc:
            self.last_ready_state = {
                "ready": False,
                "backend": self.backend_name(),
                "reason": "reindex_failed",
                "count": 0,
                "error": str(exc),
            }
            return self.last_ready_state

    #真正執行檢索。
    #先確認索引可不可用，不可用就直接回傳空結果。
    #如果 Chroma 可用，就優先用 Chroma 查詢最相近的 FAQ。
    #如果 Chroma 查不到，或不可用，就退回 JSON 檢索。
    #回傳值是「找到的 FAQ 列表 + 使用的 backend 名稱」。
    def retrieve(self, message, faq_items, vector_store):
        if not self.has_usable_vector_index(faq_items, vector_store):
            self.last_ready_state = {
                "ready": False,
                "backend": self.backend_name(),
                "reason": "not_ready",
                "count": 0,
                "error": None,
            }
            return [], self.backend_name()

        if self.has_usable_chroma_index():
            collection = self.get_chroma_collection()
            if collection is None:
                return self._retrieve_from_json(message, faq_items, vector_store)
            query_embedding = self.openai_service.embed_texts([message])[0]["embedding"]
            result = collection.query(query_embeddings=[query_embedding], n_results=3, include=["metadatas", "distances"])
            ids = result.get("ids", [[]])[0]
            if not ids:
                return self._retrieve_from_json(message, faq_items, vector_store)
            faq_map = {item["id"]: item for item in faq_items}
            self.last_ready_state = {
                "ready": True,
                "backend": "chroma",
                "reason": "already_indexed",
                "count": collection.count(),
                "error": None,
            }
            return [faq_map[faq_id] for faq_id in ids if faq_id in faq_map], "chroma"

        return self._retrieve_from_json(message, faq_items, vector_store)

    #JSON 版的檢索邏輯。
    #先把使用者訊息轉成 embedding，再和每筆 FAQ embedding 算 cosine similarity。
    #依分數排序後，取前 3 筆，且只保留分數大於 0.15 的結果。
    def _retrieve_from_json(self, message, faq_items, vector_store):
        query_embedding = self.openai_service.embed_texts([message])[0]["embedding"]
        scored = []
        for item in faq_items:
            entry = self.find_vector_entry(vector_store, item["id"])
            if not entry or entry.get("model") != self.config.embedding_model or not entry.get("embedding"):
                continue
            scored.append((cosine_similarity(query_embedding, entry["embedding"]), item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        self.last_ready_state = {
            "ready": True,
            "backend": "json",
            "reason": "already_indexed",
            "count": len(vector_store.get("entries", [])),
            "error": None,
        }
        return [item for score, item in scored[:3] if score > 0.15], "json"

    #回傳目前預設使用哪個 backend。
    #有 chromadb 就是 "chroma"，不然就是 "json"。
    def backend_name(self):
        return "chroma" if chromadb is not None else "json"

    #回傳目前最新的索引狀態資訊。
    #通常給外部查看系統現在是不是 ready、用了哪個 backend、有沒有錯誤。
    def get_last_ready_state(self):
        return dict(self.last_ready_state)
