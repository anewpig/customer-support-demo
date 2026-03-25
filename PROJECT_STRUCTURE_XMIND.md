# AI 智慧客服系統

## 專案目的

### 這個專案在做什麼
- 建立一個可部署的 AI 智慧客服系統
- 提供前台顧客問答介面
- 提供後台客服人員操作介面
- 結合 LLM、RAG、Multi-Agent、Data Cleaning、向量資料庫、SQLite、測試與 CI

### 專案核心能力
- 顧客在 UI 輸入問題
- 後端先做問題分類
- 先做 RAG 檢索 FAQ 知識庫
- 再把問題、歷史對話、檢索內容送給 OpenAI
- 產生 AI 客服回覆
- 若無法安全回答則轉人工客服
- 重要資料寫入 SQLite

## 專案目錄

### 根目錄

#### `server.py`
- 專案啟動入口
- 只負責呼叫 `app.server.run()`

#### `README.md`
- 專案說明文件
- 包含啟動方式
- 部署方式
- 測試方式
- badges 顯示位置

#### `requirements.txt`
- 執行期依賴
- 目前主要是 `chromadb`

#### `requirements-dev.txt`
- 開發期依賴
- 包含：
- `black`
- `ruff`
- `coverage`
- `pre-commit`

#### `.env.example`
- 環境變數範例
- 包含：
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_EMBEDDING_MODEL`
- `PORT`

#### `.gitignore`
- Git 忽略規則
- 忽略：
- `.env`
- 虛擬環境
- `__pycache__`
- `data/app.db`
- `data/vector_store.json`
- `data/chroma_db`

#### `Dockerfile`
- Docker 部署設定

#### `render.yaml`
- Render 部署設定

#### `nixpacks.toml`
- Railway / Nixpacks 部署設定

#### `pyproject.toml`
- Python 工具設定
- 管理：
- `black`
- `ruff`
- `coverage`

#### `.pre-commit-config.yaml`
- pre-commit hooks 設定
- 包含：
- ruff
- ruff-format
- black

#### `Makefile`
- 常用開發指令
- 包含：
- `make test`
- `make coverage`
- `make lint`
- `make format`

#### `TESTING.md`
- 測試說明文件
- 說明：
- 測試分層
- coverage 執行方式
- lint / format 指令
- pre-commit 使用方式

#### `CONTRIBUTING.md`
- 協作指南
- 說明：
- 開發環境
- branch 命名
- commit 建議
- PR 建議
- 文件同步規則

#### `PROJECT_STRUCTURE_XMIND.md`
- 給 XMind 匯入用的完整專案說明檔

### `.github/`
- GitHub 協作與 CI 設定

#### `.github/workflows/tests.yml`
- GitHub Actions workflow
- 自動執行：
- lint
- black check
- unittest
- coverage

#### `.github/pull_request_template.md`
- Pull Request 模板
- 內容包含：
- Summary
- Why
- Testing
- Risk
- Notes

#### `.github/ISSUE_TEMPLATE/bug_report.md`
- Bug report 模板

#### `.github/ISSUE_TEMPLATE/feature_request.md`
- Feature request 模板

### `app/`
- 後端主程式資料夾
- 核心邏輯都在這裡

#### `app/__init__.py`
- package 標記檔

#### `app/config.py`
- 集中管理設定
- 包含：
- OpenAI 設定
- 路徑設定
- SQLite 路徑
- static 路徑
- HOST / PORT

#### `app/server.py`
- 後端組裝入口
- 建立：
- config
- repositories
- services
- web handler
- 啟動 HTTP server

### `app/repositories/`
- 資料存取層

#### `app/repositories/__init__.py`
- package 標記檔

#### `app/repositories/json_repository.py`
- JSON 檔案讀寫
- 目前主要用於：
- FAQ seed
- vector store fallback

#### `app/repositories/sqlite_repository.py`
- SQLite repository
- 管理：
- FAQ
- conversations
- sessions
- 功能：
- 建表
- FAQ seed
- FAQ upsert
- conversation insert / list
- session get / upsert

### `app/services/`
- 商業邏輯層

#### `app/services/__init__.py`
- package 標記檔

#### `app/services/cleaning_service.py`
- Data Cleaning pipeline
- 功能：
- normalize whitespace
- normalize text
- normalize keyword
- FAQ 去重
- keyword 去重
- 無效 FAQ 過濾

#### `app/services/openai_service.py`
- OpenAI API 封裝
- 功能：
- Embeddings API
- Responses API
- previous_response_id 多輪延續
- 錯誤處理

#### `app/services/vector_store_service.py`
- 向量儲存服務
- 支援：
- Chroma
- JSON fallback vector store
- 功能：
- FAQ 轉 document
- document checksum
- reindex
- similarity retrieve
- usable index 判斷

#### `app/services/chat_service.py`
- 核心 orchestration 層
- 功能：
- 載入 FAQ
- 載入 conversations
- 載入 sessions
- 載入 vector store
- 問題分類
- RAG 檢索
- 歷史對話整理
- 呼叫 OpenAI
- fallback 回答
- human handoff 判斷
- 建立 ticket
- 更新 SQLite session
- 寫入 conversation
- FAQ 更新

### `app/web/`
- API / HTTP 層

#### `app/web/__init__.py`
- package 標記檔

#### `app/web/handler.py`
- HTTP request handler
- 處理：
- `/`
- `/healthz`
- `/api/status`
- `/api/faq`
- `/api/conversations`
- `/api/chat`
- `/api/reindex`
- 功能：
- 接收請求
- 呼叫 chat service
- 回傳 JSON
- 提供靜態頁面

### `static/`
- 前端程式

#### `static/index.html`
- 前端畫面骨架
- 包含：
- Topbar
- Hero
- 顧客聊天區
- 後台操作區
- FAQ 新增表單
- FAQ 清單

#### `static/styles.css`
- 前端樣式
- 管理：
- 排版
- 色彩
- 卡片
- 輸入框
- 響應式設計

#### `static/app.js`
- 前端互動邏輯
- 功能：
- 建立 session_id
- 發送聊天訊息
- 顯示 AI 回覆
- 顯示 RAG 來源
- 顯示 trace
- 讀取 FAQ
- 讀取 conversations
- 重建向量索引
- 顯示錯誤提示

### `data/`
- 本地資料與持久化層

#### `data/app.db`
- 正式資料庫檔案
- 使用 SQLite
- 存放：
- FAQ
- conversations
- sessions

#### `data/faq.json`
- FAQ seed 資料
- 初次啟動時可用來初始化 SQLite

#### `data/conversations.json`
- 舊版 JSON conversations
- 現在正式資料以 SQLite 為主

#### `data/sessions.json`
- 舊版 JSON sessions
- 現在正式資料以 SQLite 為主

#### `data/vector_store.json`
- JSON fallback 向量儲存

#### `data/chroma_db/`
- Chroma 持久化資料夾

### `tests/`
- 測試資料夾

#### `tests/test_cleaning_service.py`
- 測試 data cleaning

#### `tests/test_sqlite_repository.py`
- 測試 SQLite repository

#### `tests/test_chat_service.py`
- 測試 chat service 主流程

#### `tests/test_vector_store_service.py`
- 測試向量檢索流程

#### `tests/test_handler.py`
- 測試 handler API 流程

## 系統資料流程

### 總流程
- 使用者在前端輸入問題
- 前端把問題送到 `/api/chat`
- `handler.py` 收到請求
- `chat_service.py` 接手主流程
- 從 SQLite 載入 FAQ / conversations / sessions
- 先做 intent classification
- 再做 RAG retrieval
- 再整理歷史對話
- 再呼叫 OpenAI
- 產生回覆
- 回傳到前端 UI
- 若需要則標記人工處理
- 對話紀錄寫進 SQLite
- session 狀態寫進 SQLite

### Data Cleaning 流程
- FAQ seed 載入
- `cleaning_service.py` 清洗
- 去重與標準化
- 清洗後資料才進 indexing 與查詢

### RAG 流程
- FAQ 由 SQLite 提供正式資料
- 向量儲存由：
- Chroma
- 或 JSON fallback
- 查詢時優先向量檢索
- 不可用則退回 keyword retrieval

### LLM 流程
- 收到顧客問題
- 取出歷史對話
- 取出 RAG 結果
- 組 prompt
- 呼叫 OpenAI Responses API
- 回傳客服回答
- OpenAI 不可用時改走本地 fallback

### Session 流程
- 前端建立 `session_id`
- 每次請求都附帶 `session_id`
- 後端用 SQLite 找到這個 session 的歷史資料
- 對話完成後更新 SQLite session

### Human Handoff 流程
- 若檢索不到答案
- 或使用者要求真人客服
- 或出現高風險 / 高情緒詞
- 系統會標記 `needs_handoff = true`
- 後台會顯示待人工案件

## 測試與品質流程

### 測試
- 使用 `unittest`
- 目前有 12 個測試
- 覆蓋：
- cleaning
- sqlite repository
- chat service
- vector store service
- handler

### Coverage
- 使用 `coverage`
- 指令：
- `make coverage`

### Lint / Format
- 使用：
- `ruff`
- `black`
- 指令：
- `make lint`
- `make format`

### Pre-commit
- 使用 `.pre-commit-config.yaml`
- commit 前可自動檢查格式與 lint

### CI
- GitHub Actions 自動執行：
- lint
- format check
- tests
- coverage

## 面試講解版本

### 一句話
- 這是一個有前後台、可部署、可維護、帶有工程化流程的 AI 智慧客服系統

### 工程面重點
- UI 收問題
- Data Cleaning 先清資料
- RAG 檢索 FAQ
- LLM 生成回答
- Session 保存上下文
- Handoff 轉人工
- SQLite 持久化
- Chroma / JSON fallback 向量儲存
- 測試、coverage、pre-commit、CI 都有補

### 最重要的核心檔案
- `app/services/chat_service.py`
- `app/services/vector_store_service.py`
- `app/services/openai_service.py`
- `app/services/cleaning_service.py`
- `app/repositories/sqlite_repository.py`
- `app/web/handler.py`
