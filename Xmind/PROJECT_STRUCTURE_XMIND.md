# SupportOS AI Customer Support Demo

## 專案在做什麼

### 專案目標
- 建立一個可部署的 AI 智慧客服系統
- 同時提供顧客聊天頁與內部客服操作台
- 展示 LLM、RAG、Data Cleaning、向量檢索、工單流程、訂單查詢與登入權限

### 核心能力
- 顧客在網頁輸入問題
- 後端先做意圖判斷
- FAQ 題型先做 RAG 檢索
- 訂單題型直接查 SQLite 訂單資料
- 再把問題、歷史對話、FAQ context 送給 OpenAI
- 若不適合 AI 單獨處理，就建立人工工單
- 客服可在後台查看工單、訂單、聊天紀錄、FAQ 缺口與 AI 建議回覆

## 資料流程

### 顧客聊天流程
- 顧客在 `static/index.html` 輸入問題
- `static/customer.js` 呼叫 `/api/chat`
- `app/web/handler.py` 接收請求
- `app/services/chat_service.py` 決定要查 FAQ、查訂單，或直接進聊天流程
- FAQ 題型會透過 `app/services/vector_store_service.py` 做向量或關鍵字檢索
- 若有 OpenAI key，`app/services/openai_service.py` 會呼叫 Responses API 產生回覆
- 對話最後寫入 SQLite，由 `app/repositories/sqlite_repository.py` 負責持久化

### 內部客服流程
- 客服先在 `static/login.html` 登入
- `static/login.js` 呼叫 `/api/admin/login`
- 登入後進入 `static/admin.html`
- `static/admin.js` 讀取 `/api/faq`、`/api/conversations`、`/api/orders`、`/api/status`
- 客服可以更新工單狀態、查看聊天明細、複製 AI 建議回覆、搜尋訂單與補 FAQ

### RAG 流程
- FAQ seed 來自 `data/faq.json`
- `app/services/cleaning_service.py` 先做資料清洗
- `app/services/vector_store_service.py` 建立向量索引
- 有 Chroma 就用 `data/chroma_db/`
- 沒有 Chroma 就退回 `data/vector_store.json`
- 查詢時先走向量檢索，失敗再退回 keyword retrieval

## 專案結構圖

### 主要目錄樹
```text
customer-support-demo/
├── server.py
├── README.md
├── PROJECT_STRUCTURE_XMIND.md
├── TESTING.md
├── CONTRIBUTING.md
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml
├── Makefile
├── Dockerfile
├── render.yaml
├── nixpacks.toml
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── .github/
│   ├── workflows/tests.yml
│   ├── pull_request_template.md
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── server.py
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── json_repository.py
│   │   └── sqlite_repository.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── chat_service.py
│   │   ├── cleaning_service.py
│   │   ├── openai_service.py
│   │   └── vector_store_service.py
│   └── web/
│       ├── __init__.py
│       └── handler.py
├── static/
│   ├── index.html
│   ├── admin.html
│   ├── login.html
│   ├── customer.js
│   ├── admin.js
│   ├── login.js
│   └── styles.css
├── data/
│   ├── faq.json
│   ├── orders.json
│   ├── app.db
│   ├── conversations.json
│   ├── sessions.json
│   ├── vector_store.json
│   └── chroma_db/
└── tests/
    ├── test_chat_service.py
    ├── test_cleaning_service.py
    ├── test_handler.py
    ├── test_sqlite_repository.py
    └── test_vector_store_service.py
```

## 根目錄檔案

### `server.py`
- 最外層啟動入口
- 只負責呼叫 `app.server.run()`

### `README.md`
- GitHub 首頁說明
- 包含專案介紹、啟動方式、環境變數、部署方式與功能摘要

### `PROJECT_STRUCTURE_XMIND.md`
- 給 XMind 匯入的專案結構說明檔
- 內容以心智圖友善格式整理

### `TESTING.md`
- 測試與品質檢查說明
- 包含 unittest、coverage、lint、format、pre-commit 的使用方式

### `CONTRIBUTING.md`
- 專案協作指南
- 說明如何開發、如何提 PR、如何維持文件與測試一致

### `requirements.txt`
- 執行期依賴
- 目前主要是 `chromadb`

### `requirements-dev.txt`
- 開發期依賴
- 包含 `black`、`ruff`、`coverage`、`pre-commit`

### `pyproject.toml`
- Python 工具設定檔
- 管理 `black`、`ruff`、`coverage`

### `Makefile`
- 常用指令入口
- 包含 `make test`、`make lint`、`make format`、`make coverage`

### `Dockerfile`
- Docker 容器部署設定

### `render.yaml`
- Render 部署設定

### `nixpacks.toml`
- Railway / Nixpacks 部署設定

### `.env.example`
- 環境變數範例
- 包含 OpenAI 設定與後台帳密設定

### `.gitignore`
- Git 忽略規則
- 忽略 `.env`、虛擬環境、快取檔與本地資料庫

### `.pre-commit-config.yaml`
- pre-commit hooks 設定檔
- 用來在 commit 前跑格式化與靜態檢查

## `.github/`

### `.github/workflows/tests.yml`
- GitHub Actions workflow
- 會在 push / pull request 時自動跑 lint、format check、測試與 coverage

### `.github/pull_request_template.md`
- Pull Request 模板
- 幫助整理變更摘要、測試方式與風險

### `.github/ISSUE_TEMPLATE/bug_report.md`
- Bug 回報模板

### `.github/ISSUE_TEMPLATE/feature_request.md`
- 功能需求模板

## `app/`

### `app/__init__.py`
- Python package 標記檔

### `app/config.py`
- 專案設定中心
- 讀取 `.env`
- 提供資料夾路徑、OpenAI 參數、管理員帳密、HOST、PORT

### `app/server.py`
- 後端組裝入口
- 建立 config、repository、service、handler
- 啟動 `ThreadingHTTPServer`

## `app/repositories/`

### `app/repositories/__init__.py`
- package 標記檔

### `app/repositories/json_repository.py`
- JSON 讀寫工具
- 主要給 FAQ seed 與向量 fallback 使用

### `app/repositories/sqlite_repository.py`
- SQLite 資料存取層
- 建立與管理 `faq_items`、`conversations`、`sessions`、`orders`
- 會初始化資料表、建立索引、seed FAQ 與 seed orders
- 提供 FAQ upsert、對話存取、session 更新、訂單搜尋與工單流程更新

## `app/services/`

### `app/services/__init__.py`
- package 標記檔

### `app/services/auth_service.py`
- 管理後台登入權限
- 用 `.env` 中的 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 驗證
- 成功登入後建立 session token
- 提供登入、查 session、登出

### `app/services/cleaning_service.py`
- FAQ Data Cleaning pipeline
- 做文字標準化、空白清理、關鍵字去重、FAQ 去重與無效資料過濾

### `app/services/openai_service.py`
- OpenAI API 封裝層
- 負責 Responses API 與 Embeddings API
- 支援多輪對話 `previous_response_id`
- 負責工單摘要 / AI 建議回覆
- 負責 runtime 狀態紀錄，例如正常、異常、額度不足

### `app/services/vector_store_service.py`
- 向量儲存與檢索服務
- 支援 Chroma 與 JSON fallback
- 負責 FAQ 轉 document、reindex、相似度查詢、索引可用性判斷

### `app/services/chat_service.py`
- 專案核心 orchestration 層
- 負責聊天主流程、意圖分類、RAG、歷史對話組裝、訂單驗證、fallback 回答、工單建立與 FAQ 缺口分析
- 也是 `/api/status`、工單摘要、聊天紀錄、訂單列表等後台資料的主要來源

## `app/web/`

### `app/web/__init__.py`
- package 標記檔

### `app/web/handler.py`
- HTTP API 與靜態頁面入口
- 處理：
- `/`
- `/login.html`
- `/admin.html`
- `/healthz`
- `/api/status`
- `/api/admin/login`
- `/api/admin/logout`
- `/api/admin/session`
- `/api/chat`
- `/api/faq`
- `/api/conversations`
- `/api/conversations/workflow`
- `/api/orders`
- `/api/analysis/faq-gaps`
- `/api/tickets/assistance`
- `/api/reindex`

## `static/`

### `static/index.html`
- 顧客前台頁面
- 顯示聊天視窗、驗證欄位、常見問題下拉選單與輸入框

### `static/admin.html`
- 內部客服操作台頁面
- 顯示工單列表、聊天紀錄、session 對話明細、FAQ 表單、FAQ 缺口分析、訂單列表、OpenAI 狀態卡與 AI 建議回覆區

### `static/login.html`
- 後台登入頁
- 讓客服輸入帳密進入操作台

### `static/customer.js`
- 顧客頁互動邏輯
- 管理 session id、送出聊天、顯示訊息時間、訂單驗證欄位、熱門問題快捷操作

### `static/admin.js`
- 後台頁互動邏輯
- 負責載入 FAQ、工單、聊天紀錄、FAQ 缺口、訂單列表、OpenAI runtime 狀態
- 支援工單更新、AI 協助整理、複製建議回覆、FAQ 表單填入與登出

### `static/login.js`
- 登入頁互動邏輯
- 呼叫登入 API
- 顯示帳號錯誤、密碼錯誤、session 過期等提示

### `static/styles.css`
- 全站共用樣式
- 同時管理顧客頁、登入頁、後台操作台的視覺與排版

## `data/`

### `data/faq.json`
- FAQ seed 資料
- 專案第一次啟動時可用來灌入知識庫

### `data/orders.json`
- 訂單 seed 資料
- 提供示範用訂單查詢內容

### `data/app.db`
- SQLite 主資料庫
- 實際保存 FAQ、訂單、對話、session

### `data/conversations.json`
- 舊版或過渡期對話資料檔
- 現在主要資料來源已是 SQLite

### `data/sessions.json`
- 舊版或過渡期 session 資料檔
- 現在主要資料來源已是 SQLite

### `data/vector_store.json`
- JSON 版向量儲存 fallback
- 當 Chroma 不可用時使用

### `data/chroma_db/`
- Chroma 持久化資料夾
- 儲存 FAQ 向量索引

## `tests/`

### `tests/test_chat_service.py`
- 測試聊天主流程
- 包含退款回答、訂單查詢、工單摘要、status 狀態等

### `tests/test_cleaning_service.py`
- 測試 FAQ data cleaning 邏輯

### `tests/test_handler.py`
- 測試 API handler
- 包含 `/healthz`、`/api/status`、登入、工單摘要、訂單 API 等

### `tests/test_sqlite_repository.py`
- 測試 SQLite repository
- 驗證 FAQ、對話、session、訂單等資料存取邏輯

### `tests/test_vector_store_service.py`
- 測試向量檢索服務
- 驗證 reindex、retrieve 與索引可用性判斷

## 你可以怎麼理解這個專案

### 一句話版本
- 這是一個有顧客端、內部客服端、RAG、LLM、訂單查詢與人工工單流程的 AI 客服系統

### 工程分層版本
- `static/` 是前端頁面與互動
- `app/web/` 是 HTTP API 層
- `app/services/` 是商業邏輯層
- `app/repositories/` 是資料存取層
- `data/` 是 seed 與本地持久化資料
- `tests/` 是測試保護

### 面試講法版本
- 這個專案不是單純聊天機器人，而是把 FAQ 清洗、RAG、OpenAI、訂單資料庫、人工接手流程、後台操作台與登入權限整合成一個完整 AI application
