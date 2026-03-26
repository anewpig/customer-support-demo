# SupportOS 專案教學版

## 先用一句話理解這個專案

### 這是什麼
- 這是一個 AI 智慧客服系統
- 顧客可以在前台網頁問問題
- 系統會先查 FAQ 或訂單資料
- 再決定要用 AI 回答，或轉給真人客服
- 內部客服有自己的登入頁與操作台

### 這個專案不是什麼
- 不是單純聊天機器人
- 不是只有呼叫 OpenAI API 的小 demo
- 不是只有前端畫面

### 它真正展示的是
- `LLM`
- `RAG`
- `Data Cleaning`
- `向量資料庫`
- `訂單查詢`
- `人工工單流程`
- `登入與權限`
- `前後台分離`

## 你要先建立的 3 個觀念

### 觀念 1：這個專案有兩個使用者
- 顧客
- 內部客服人員

### 觀念 2：這個專案有兩條主要流程
- 顧客聊天流程
- 內部客服處理流程

### 觀念 3：這個專案是分層的
- 前端層：畫面與互動
- API 層：收 request / 回 response
- Service 層：商業邏輯
- Repository 層：資料存取
- Data 層：SQLite、FAQ、orders、向量資料

## 專案的整體架構

### 一句話版本
- 顧客在前台發問，後端先分類，再查 FAQ 或查訂單，之後用 OpenAI 產生回覆；如果 AI 不適合處理，就建立工單讓客服接手

### 用系統架構來看
- `static/`
  - 顧客頁
  - 客服頁
  - 登入頁
- `app/web/`
  - HTTP API
- `app/services/`
  - 核心邏輯
- `app/repositories/`
  - SQLite / JSON 存取
- `data/`
  - FAQ、訂單、向量資料、SQLite DB
- `tests/`
  - 單元測試

## 我建議你怎麼讀這個專案

### 第一步：先看最外層入口
- `server.py`
- `app/server.py`

### 第二步：看 request 進來後去哪裡
- `app/web/handler.py`

### 第三步：看真正的核心流程
- `app/services/chat_service.py`

### 第四步：再去看周邊服務
- `app/services/openai_service.py`
- `app/services/vector_store_service.py`
- `app/services/cleaning_service.py`
- `app/services/auth_service.py`

### 第五步：最後看資料怎麼存
- `app/repositories/sqlite_repository.py`
- `data/faq.json`
- `data/orders.json`

## 專案的主要資料夾

### 根目錄

#### `server.py`
- 真正的執行入口
- 很薄
- 只是把流程交給 `app.server.run()`

#### `README.md`
- 給 GitHub 首頁看的說明
- 告訴別人這個專案怎麼跑

#### `PROJECT_STRUCTURE_XMIND.md`
- 偏結構圖
- 主要是說「有哪些檔案、各自做什麼」

#### `PROJECT_TEACHING_XMIND.md`
- 這份教學版文件
- 主要是說「你應該怎麼理解整個專案」

#### `TESTING.md`
- 告訴你怎麼跑測試、coverage、lint、format

#### `CONTRIBUTING.md`
- 團隊協作規則
- 偏工程流程文件

### `app/`
- 後端真正的程式碼
- 幾乎所有核心都在這裡

### `static/`
- 前端畫面
- 你看到的顧客頁、客服頁、登入頁都在這裡

### `data/`
- 資料來源與持久化內容

### `tests/`
- 測試保護

## `app/` 裡面的角色分工

### `app/config.py`
- 專案的設定中心
- 讀 `.env`
- 決定：
  - OpenAI key
  - model
  - embedding model
  - admin 帳密
  - sqlite 路徑
  - static 路徑
  - host / port

### `app/server.py`
- 把所有零件組裝起來
- 建立：
  - config
  - cleaning service
  - openai service
  - auth service
  - vector store service
  - sqlite repository
  - chat service
  - handler
- 最後啟動 HTTP server

### `app/web/handler.py`
- 所有 API 的入口
- 可以把它想成門口櫃台
- 它本身不做太多業務邏輯
- 它只是把請求分派給對的 service

### `app/services/chat_service.py`
- 這是整個專案的核心
- 幾乎所有你在面試時要講的主流程都在這裡
- 它負責：
  - 分類使用者意圖
  - FAQ 檢索
  - 訂單查詢
  - 訂單驗證
  - 歷史對話整理
  - 呼叫 OpenAI
  - fallback 回答
  - 是否需要人工客服
  - 工單摘要資料
  - FAQ 缺口分析
  - status 資訊

### `app/services/openai_service.py`
- 專門跟 OpenAI 溝通
- 你可以把它想成 API adapter
- 它負責：
  - Embeddings
  - Responses API
  - 多輪對話 previous_response_id
  - staff assistance
  - OpenAI runtime 狀態紀錄

### `app/services/vector_store_service.py`
- 專門處理向量索引和檢索
- 它的工作是：
  - FAQ 轉 document
  - FAQ 做 embedding
  - 建立 Chroma index
  - 沒有 Chroma 時退回 JSON vector store
  - 相似度搜尋

### `app/services/cleaning_service.py`
- 專門清理 FAQ
- 因為 RAG 前資料品質很重要
- 它做的事情包括：
  - 多餘空白清理
  - keyword 去重
  - FAQ 去重
  - 欄位標準化

### `app/services/auth_service.py`
- 只處理後台登入權限
- 功能非常專一
- 它負責：
  - 驗證帳號密碼
  - 建立 admin session token
  - 查登入狀態
  - 登出

### `app/repositories/sqlite_repository.py`
- 資料庫存取層
- 把 SQL 都集中在這裡
- 上層 service 不用直接碰 sqlite 細節
- 它管理：
  - FAQ
  - conversations
  - sessions
  - orders

### `app/repositories/json_repository.py`
- 比較簡單的 JSON 工具
- 目前主要用在：
  - FAQ seed
  - orders seed
  - vector store fallback

## `static/` 裡面的角色分工

### `static/index.html`
- 顧客頁畫面骨架
- 顧客看得到的東西都在這

### `static/customer.js`
- 顧客頁邏輯
- 管理：
  - 發送訊息
  - 顯示時間
  - session id
  - 常見問題快捷操作
  - 訂單驗證欄位

### `static/admin.html`
- 後台操作台畫面骨架
- 內部人員會看的內容都在這

### `static/admin.js`
- 後台頁邏輯
- 管理：
  - FAQ 載入
  - 工單列表
  - 聊天紀錄
  - 訂單列表
  - AI 工單摘要
  - AI 建議回覆複製
  - FAQ 缺口分析
  - OpenAI 用量 / 額度狀態卡

### `static/login.html`
- 後台登入畫面

### `static/login.js`
- 登入互動邏輯
- 顯示：
  - 帳號錯誤
  - 密碼錯誤
  - session 過期

### `static/styles.css`
- 全專案樣式
- 同時管理顧客頁、登入頁、客服操作台

## `data/` 裡面的資料在做什麼

### `data/faq.json`
- FAQ seed 資料
- 可以把它想成知識庫初始資料

### `data/orders.json`
- 訂單 seed 資料
- demo 用的範例訂單

### `data/app.db`
- SQLite 主資料庫
- 真正的 FAQ、對話、session、orders 都存在這裡

### `data/vector_store.json`
- 向量資料的 fallback
- 如果 Chroma 不可用，系統還有這條備援路線

### `data/chroma_db/`
- Chroma 的持久化資料夾

### `data/conversations.json` / `data/sessions.json`
- 過渡期資料檔
- 目前主流程已經以 SQLite 為主

## 顧客問一個問題時，系統怎麼跑

### Step 1：前端送出問題
- 顧客在 `index.html` 輸入內容
- `customer.js` 把內容送到 `/api/chat`

### Step 2：後端收到 request
- `handler.py` 收到 `/api/chat`
- 把資料交給 `chat_service.compose_answer(...)`

### Step 3：判斷問題類型
- `chat_service.classify_intent()`
- 可能會判成：
  - `order_lookup`
  - `refund`
  - `shipping`
  - `payment`
  - `human_handoff`
  - `friendly_chat`

### Step 4：如果是訂單題
- 先抓出 `ORD-1001` 這種單號
- 去 SQLite 查訂單
- 再判斷有沒有驗證成功
- 有時會要求顧客提供：
  - 姓名
  - 手機末四碼

### Step 5：如果是 FAQ / 客服題
- 先做 FAQ 檢索
- 能走向量就走向量
- 不行就退回 keyword retrieval

### Step 6：組 context
- 近期對話歷史
- FAQ context
- 訂單 context
- escalation 判斷

### Step 7：呼叫 OpenAI 或 fallback
- 有 key 就走 OpenAI
- 沒 key 或 API 失敗就走本地 fallback

### Step 8：存資料
- 把對話寫進 `conversations`
- 更新 `sessions`
- 如果需要，就設成 handoff 工單

### Step 9：回到前端
- 顧客看到最終回覆
- 後台可以看到這筆案件

## 內部客服打開後台時，系統怎麼跑

### Step 1：先登入
- `login.html`
- `login.js`
- `/api/admin/login`

### Step 2：驗證 session
- `admin.js` 先打 `/api/admin/session`
- 沒登入就跳回 login

### Step 3：載入後台資料
- `/api/status`
- `/api/faq`
- `/api/conversations`
- `/api/orders`
- `/api/analysis/faq-gaps`

### Step 4：客服可以做什麼
- 更新工單狀態
- 指派客服
- 填工單備註
- 看聊天紀錄
- 查訂單
- 用 AI 協助整理工單
- 複製建議回覆
- 補 FAQ

## Multi-Agent 在這個專案裡是怎麼表現的

### 這裡不是用真的多程序 agent framework
- 沒有開很多獨立 agent process
- 也不是 LangGraph / CrewAI 那種框架

### 這裡的 Multi-Agent 比較像流程分工
- Intent Agent
- Verification Agent
- Tone Agent
- Retriever Agent
- Response Agent
- Escalation Agent

### 它的好處
- 面試時可以清楚說明每個階段負責什麼
- 邏輯比單一 chat completion 更好解釋

## RAG 在這個專案裡是怎麼做的

### 先有資料來源
- FAQ seed 在 `data/faq.json`

### 資料先清理
- `cleaning_service.py`

### 再做 embedding
- `openai_service.embed_texts()`

### 再建立向量索引
- `vector_store_service.reindex_chroma()`
- 或 `vector_store_service.reindex_json()`

### 查詢時再取回相關 FAQ
- `vector_store_service.retrieve()`

### 最後交給 LLM 組回答
- `openai_service.generate_customer_reply()`

## OpenAI 在這個專案裡做了兩件事

### 1. 顧客聊天回答
- 用 Responses API
- 回答顧客問題

### 2. 工單摘要與建議回覆
- 也是 Responses API
- 但 prompt 不同
- 目的是幫真人客服快速接手案件

## OpenAI Runtime 卡片在做什麼

### 這張卡不是顯示真正帳戶餘額
- 它不是去抓 OpenAI Billing 餘額

### 它顯示的是系統最近一次 OpenAI 請求狀態
- 正常
- 異常
- 額度不足
- 未啟用
- 後端離線

### 它有什麼用
- 客服人員一眼就知道 AI 現在能不能用
- 如果額度爆掉，不用等顧客抱怨才知道

## 訂單功能是怎麼設計的

### 這個專案不是靠 LLM 自己猜訂單
- 訂單查詢是 deterministic logic
- 因為訂單不能亂講

### 現在的做法
- 先從訊息裡抓出訂單編號
- 查 SQLite 訂單資料
- 做姓名 / 手機末四碼驗證
- 驗證通過才顯示細節

### 為什麼這樣比較合理
- LLM 適合生成語氣
- 但像訂單、狀態、物流單號這種結構化資料，應該直接查 DB

## 工單流程是怎麼設計的

### 工單什麼時候出現
- AI 判斷需要人工處理時
- 或客服風險高時

### 工單有哪些欄位
- ticket id
- session id
- customer_message
- response
- handoff_status
- handoff_notes
- assigned_to

### 工單狀態
- `pending`
- `in_progress`
- `resolved`

## FAQ 缺口分析在做什麼

### 它的核心想法
- 觀察哪些問題最常沒有被 FAQ 穩定接住

### 它的用途
- 幫你決定下一批要補什麼 FAQ

### 這很適合面試講
- 因為這代表你不只做聊天功能
- 你還有在思考知識庫如何持續改善

## 測試層在保護什麼

### `test_chat_service.py`
- 保護核心聊天流程

### `test_cleaning_service.py`
- 保護 FAQ cleaning

### `test_handler.py`
- 保護 API handler

### `test_sqlite_repository.py`
- 保護資料庫存取

### `test_vector_store_service.py`
- 保護向量檢索

## 如果你要修改功能，應該去哪裡

### 想改聊天邏輯
- `app/services/chat_service.py`

### 想改 OpenAI prompt
- `app/services/openai_service.py`

### 想改登入邏輯
- `app/services/auth_service.py`
- `static/login.js`

### 想改訂單資料庫行為
- `app/repositories/sqlite_repository.py`
- `app/services/chat_service.py`

### 想改後台畫面
- `static/admin.html`
- `static/admin.js`
- `static/styles.css`

### 想改顧客聊天頁
- `static/index.html`
- `static/customer.js`
- `static/styles.css`

### 想改 API 路由
- `app/web/handler.py`

## 如果你要 debug，建議這樣找

### 顧客送不出去
- 先看 `customer.js`
- 再看 `/api/chat`
- 再看 `handler.py`

### OpenAI 沒有回
- 先看 `.env`
- 再看 `openai_service.py`
- 再看 admin 的 OpenAI runtime 卡片

### 訂單查不到
- 先看 `orders.json`
- 再看 SQLite seed
- 再看 `chat_service.extract_order_id()`

### FAQ 沒命中
- 先看 `faq.json`
- 再看 `cleaning_service.py`
- 再看 `vector_store_service.py`

### 後台登入不進去
- 看 `.env`
- 看 `auth_service.py`
- 看 `login.js`

## 面試時你可以怎麼講這個專案

### 30 秒版本
- 這是一個可部署的 AI 智慧客服系統，前台接收顧客問題，後端先做意圖判斷，再用 FAQ RAG 或訂單資料補足 context，最後交給 OpenAI 生成回覆；如果 AI 不適合處理，就轉到後台客服工單流程

### 1 分鐘版本
- 這個專案除了基本聊天，還做了前後台分離、RAG、Data Cleaning、SQLite 訂單查詢、人工工單流程、AI 工單摘要與 FAQ 缺口分析。工程上也做了模組拆分、測試、CI 和部署設定，所以它不是單純 demo，而是比較接近可落地的 AI application

## 你現在最該記住的重點

### 重點 1
- 真正的核心在 `chat_service.py`

### 重點 2
- `handler.py` 只是 API 入口，不是商業邏輯中心

### 重點 3
- `openai_service.py` 專心處理 OpenAI

### 重點 4
- `sqlite_repository.py` 專心處理資料庫

### 重點 5
- `static/` 是 UI
- `app/` 是 backend
- `data/` 是資料

## 最後用一句話把你教會

### 這個專案的本質
- 這是一個把「客服對話、FAQ 知識庫、訂單查詢、人工接手、AI 摘要、登入權限」整合在一起的完整 AI 客服系統，而你只要抓住 `前端 -> handler -> chat_service -> 其他 service / repository` 這條主線，就能看懂整個專案
