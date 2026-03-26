# SupportOS 專案知識地圖

## 透過這個專案你可以學到什麼

### 一句話版本
- 這個專案不只是在學怎麼串 OpenAI，而是在學怎麼把 AI 能力、後端架構、資料庫、前端、測試、部署和產品設計整合成一個完整系統

## 第一層：AI 應用能力

### 1. LLM 應用設計
- 什麼問題適合交給 LLM
- 什麼問題不應該交給 LLM
- 怎麼讓 LLM 只負責生成語氣，而不是亂決策
- 怎麼讓 AI 回答自然，但又不要幻覺

### 2. Prompt Engineering
- system prompt 怎麼寫
- 怎麼控制語氣
- 怎麼控制回答長度
- 怎麼避免客服太官腔
- 怎麼設計 fallback prompt
- 怎麼區分客服模式與聊天模式

### 3. Multi-Agent 思維
- 雖然這個專案不是用 agent framework，但你可以學到 agent 分工概念
- Intent Agent
- Retriever Agent
- Verification Agent
- Response Agent
- Escalation Agent
- Tone Agent

### 4. AI 產品落地思維
- 不是每件事都要交給模型
- 訂單查詢應該走 deterministic logic
- FAQ 類問題適合走 RAG
- 摘要和建議回覆適合交給 LLM

## 第二層：RAG 與知識庫能力

### 1. RAG 流程設計
- FAQ 要先清理再進 embedding
- RAG 的資料來源怎麼準備
- 檢索結果怎麼餵給模型
- 什麼時候該向量檢索
- 什麼時候該 keyword fallback

### 2. Data Cleaning
- FAQ 為什麼不能直接丟進向量資料庫
- whitespace normalize
- keyword 去重
- FAQ 去重
- category / question / answer 欄位標準化

### 3. Embedding 與向量資料庫
- embedding model 的用途
- 向量索引是什麼
- Chroma 怎麼存資料
- JSON vector store fallback 是什麼
- reindex 在做什麼

### 4. FAQ 品質經營
- FAQ 缺口分析怎麼做
- FAQ 命中不足怎麼觀察
- 哪些問題應該補進知識庫
- FAQ 如何持續演進

## 第三層：後端工程能力

### 1. 系統分層
- API 層
- Service 層
- Repository 層
- Data 層
- 為什麼要分層
- 分層後怎麼讓維護變簡單

### 2. HTTP API 設計
- GET / POST 怎麼分
- `/api/chat`
- `/api/status`
- `/api/orders`
- `/api/faq`
- `/api/conversations`
- `/api/tickets/assistance`
- API 責任如何切分

### 3. 業務邏輯設計
- 什麼邏輯放 handler
- 什麼邏輯放 service
- 什麼邏輯放 repository
- 為什麼 `chat_service.py` 是 orchestrator

### 4. Session 與狀態管理
- 顧客 session
- Admin session
- 對話歷史怎麼保存
- previous_response_id 怎麼延續對話

## 第四層：資料庫與資料模型

### 1. SQLite 實作
- FAQ table
- conversations table
- sessions table
- orders table

### 2. Schema 設計思維
- FAQ 需要哪些欄位
- conversation 需要哪些欄位
- session 需要哪些欄位
- order 需要哪些欄位

### 3. Index 與查詢效率
- 為什麼要對 session_id 建 index
- 為什麼要對 needs_handoff 建 index
- 為什麼要對 orders 搜尋欄位建 index

### 4. Seed 與 migration 思維
- FAQ seed
- orders seed
- 舊欄位升級
- schema 演進

## 第五層：產品與流程設計

### 1. 顧客端體驗設計
- 顧客該看到什麼
- 顧客不該看到什麼
- 為什麼要隱藏 trace / RAG 細節
- 為什麼熱門問題要做成快捷選單

### 2. 後台操作台設計
- 客服為什麼需要工單列表
- 為什麼需要聊天紀錄
- 為什麼需要訂單列表
- 為什麼需要 FAQ 缺口分析
- 為什麼需要 OpenAI runtime 狀態卡

### 3. 工單流程設計
- pending / in_progress / resolved
- assigned_to
- handoff_notes
- 人工轉接時機

### 4. 訂單驗證設計
- 為什麼查訂單不能只靠單號
- 為什麼要加姓名或手機末四碼
- 怎麼兼顧安全與操作便利

## 第六層：前端能力

### 1. 前端拆分思維
- customer.js
- admin.js
- login.js
- 為什麼不要全部塞在 app.js

### 2. UI / UX 設計
- 顧客頁和 admin 頁分離
- 後台版面資訊分區
- dropdown hover 互動
- 聊天時間顯示
- 一鍵複製建議回覆

### 3. 前端與 API 串接
- fetch 請求
- admin session 處理
- 登入失敗提示
- 載入狀態與錯誤提示

## 第七層：測試與品質保證

### 1. 單元測試
- test_chat_service
- test_cleaning_service
- test_handler
- test_sqlite_repository
- test_vector_store_service

### 2. 測試思維
- 哪些邏輯值得被測
- 哪些 bug 容易回歸
- 怎麼用 fake service 減少外部依賴

### 3. 程式碼品質工具
- ruff
- black
- coverage
- pre-commit

### 4. CI/CD 基礎
- GitHub Actions
- push / pull request 自動測試

## 第八層：部署與維運

### 1. 部署能力
- Render
- Railway
- Docker

### 2. 環境變數管理
- `.env`
- `.env.example`
- OpenAI key
- admin 帳密

### 3. 健康檢查與運行狀態
- `/healthz`
- `/api/status`
- OpenAI runtime 狀態卡

### 4. 維運思維
- 額度不足怎麼提示
- 後端離線怎麼發現
- 模型失敗時怎麼 fallback

## 第九層：效能與可擴充性

### 1. 效能優化
- 減少不必要的 reload
- 限制 history context 長度
- 減少 FAQ context 長度
- 訂單查詢不要交給 LLM

### 2. 可擴充性
- SQLite 之後可以換 PostgreSQL
- `http.server` 之後可以換 FastAPI
- Chroma 之後可以換雲端向量資料庫
- Auth 之後可以換正式 RBAC

### 3. 高併發思維
- 現在這版適合 demo，不適合 3000 同時併發
- 要升級時會遇到：
  - web server 瓶頸
  - SQLite 寫入瓶頸
  - OpenAI rate limit
  - 向量索引查詢瓶頸

## 第十層：資訊安全與風險控制

### 1. 權限控管
- 顧客頁和 admin 頁分離
- admin API 要登入

### 2. 敏感資料保護
- API key 不進前端
- 訂單資料不讓未驗證使用者直接拿到

### 3. 風險控管
- 人工客服 escalation
- 額度不足警示
- API 錯誤 fallback

## 第十一層：面試能力

### 1. 你可以學到怎麼講專案
- 先講使用者問題
- 再講系統流程
- 再講技術實作
- 最後講擴充方向

### 2. 你可以學到怎麼拆解系統
- UI 層
- API 層
- orchestration 層
- service 層
- repository 層
- data 層

### 3. 你可以學到怎麼回答深問
- 為什麼訂單查詢不用 LLM 直接回答
- 為什麼要加 Data Cleaning
- 為什麼要分 customer / admin 頁
- 為什麼要做 FAQ 缺口分析

## 如果你要繼續往下學，我建議的優先順序

### 第一優先
- Prompt Engineering
- RAG 設計
- LLM 與結構化資料如何分工

### 第二優先
- 後端分層架構
- SQLite / SQL schema 設計
- 測試與 CI

### 第三優先
- 部署
- 效能優化
- 可擴充架構

### 第四優先
- 角色權限
- 通知系統
- PostgreSQL / FastAPI / 雲端向量庫

## 最後用一句話幫你總結

### 這個專案能教你的核心
- 這個專案能讓你同時學會「AI 應用怎麼落地」和「軟體系統怎麼工程化」，因為它把模型、資料、流程、權限、測試、部署全部放在同一個真實情境裡
