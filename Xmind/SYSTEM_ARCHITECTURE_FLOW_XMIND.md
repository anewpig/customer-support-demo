# SupportOS 系統架構與資料流

## 一句話總覽

### 這個系統的本質
- 這是一個前後台分離的 AI 智慧客服系統
- 前台接收顧客問題
- 後端整合 FAQ、訂單資料、OpenAI、RAG 與人工工單流程
- 後台讓客服查看工單、聊天紀錄、訂單、FAQ 缺口與 AI 建議回覆

## 系統架構圖

### Block View
```text
+-------------------+        +-------------------+
| Customer UI       |        | Admin UI          |
| index.html        |        | admin.html        |
| customer.js       |        | admin.js          |
+---------+---------+        +---------+---------+
          |                            |
          +------------+   +-----------+
                       |   |
                 +-----v---v------------------+
                 | HTTP / API Layer           |
                 | app/web/handler.py         |
                 +-----+----------------------+
                       |
                 +-----v----------------------+
                 | Chat Orchestration Layer   |
                 | app/services/chat_service  |
                 +--+-----------+----------+--+
                    |           |          |
         +----------v--+   +----v-----+    +------------------+
         | OpenAI      |   | Vector   |    | Auth Service     |
         | Service     |   | Store    |    | admin login      |
         +------+------|   +----+-----+    +------------------+
                |               |
         +------v------+   +----v------------------+
         | OpenAI API  |   | Chroma / JSON Vector  |
         +-------------+   +-----------------------+

                    +------------------------------+
                    | SQLite Repository            |
                    | FAQ / Orders / Conversations |
                    | Sessions                     |
                    +--------------+---------------+
                                   |
                             +-----v-----+
                             | SQLite DB |
                             | data/app.db
                             +-----------+
```

## 系統分層

### 1. 前端層
- 顧客頁
- 登入頁
- 客服操作台

### 2. API 層
- 接收前端 request
- 驗證登入狀態
- 回傳 JSON 或靜態頁面

### 3. 核心邏輯層
- 問題分類
- FAQ 檢索
- 訂單查詢
- 工單建立
- AI 回覆與摘要

### 4. 能力服務層
- OpenAI Service
- Vector Store Service
- Auth Service
- Cleaning Service

### 5. 資料存取層
- SQLite Repository
- JSON Repository

### 6. 資料層
- SQLite
- FAQ seed
- Orders seed
- Vector store
- Chroma

## 主要系統元件

### Customer UI
- 顧客發問入口
- 顯示聊天內容
- 收集訂單驗證資訊

### Admin UI
- 客服後台入口
- 顯示工單、聊天紀錄、訂單、FAQ 缺口
- 顯示 OpenAI runtime 狀態

### Handler API
- 系統門口
- 將 request 分派到正確的 service

### Chat Service
- 系統大腦
- 負責串接 FAQ、訂單、OpenAI、工單流程

### OpenAI Service
- 呼叫 Responses API
- 呼叫 Embeddings API
- 紀錄 runtime 狀態

### Vector Store Service
- 管理 FAQ 向量索引
- 檢索相似 FAQ

### Auth Service
- 後台登入與 session 驗證

### SQLite Repository
- 管理 FAQ
- 管理 conversations
- 管理 sessions
- 管理 orders

## 主要資料流

### 1. 顧客聊天資料流
```text
[Customer UI]
    ->
[POST /api/chat]
    ->
[Handler]
    ->
[Chat Service]
    ->
[Intent 判斷]
    ->
[FAQ 檢索 or 訂單查詢]
    ->
[OpenAI / fallback]
    ->
[寫入 conversations + sessions]
    ->
[回傳顧客頁]
```

### 2. FAQ / RAG 資料流
```text
[faq.json / SQLite FAQ]
    ->
[Cleaning Service]
    ->
[Vector Store Service]
    ->
[Chroma 或 JSON Vector Store]
    ->
[查詢時 retrieve 相似 FAQ]
    ->
[交給 Chat Service 組 context]
```

### 3. 訂單查詢資料流
```text
[Customer 問訂單]
    ->
[Chat Service 抓 order_id]
    ->
[SQLite Repository 查 orders]
    ->
[驗證姓名 / 手機末四碼]
    ->
[組訂單 context]
    ->
[回傳顧客]
```

### 4. 人工工單資料流
```text
[顧客問題]
    ->
[Chat Service 判斷需人工處理]
    ->
[建立 handoff ticket]
    ->
[寫入 conversations]
    ->
[Admin UI 讀取待處理案件]
    ->
[客服更新狀態 / 指派 / 備註]
```

### 5. 工單摘要與 AI 建議回覆資料流
```text
[Admin 點選工單]
    ->
[GET /api/tickets/assistance]
    ->
[Chat Service 組工單內容 + session 歷史 + FAQ context]
    ->
[OpenAI Service]
    ->
[回傳 summary + suggested reply]
    ->
[Admin UI 顯示]
```

### 6. 後台登入資料流
```text
[Login UI]
    ->
[POST /api/admin/login]
    ->
[Auth Service 驗證帳密]
    ->
[建立 session token]
    ->
[Set-Cookie]
    ->
[Admin UI]
```

## 後台資料讀取流

### 後台首頁載入時
```text
[Admin UI]
    ->
[GET /api/status]
[GET /api/faq]
[GET /api/conversations]
[GET /api/orders]
[GET /api/analysis/faq-gaps]
    ->
[Handler]
    ->
[Chat Service / Repository / OpenAI runtime]
    ->
[回傳後台畫面]
```

## 系統中的資料來源

### 結構化資料
- SQLite `orders`
- SQLite `conversations`
- SQLite `sessions`
- SQLite `faq_items`

### 非結構化知識
- FAQ 文字內容
- FAQ keywords
- FAQ 向量索引

### 外部服務
- OpenAI Responses API
- OpenAI Embeddings API

## 系統中的關鍵判斷點

### 問題分類
- 先判斷是不是訂單題
- 再判斷是不是退款 / 出貨 / 付款 / 真人客服
- 不屬於客服題就偏向 friendly chat

### 回答來源
- 訂單題：優先用 SQLite 直接查
- FAQ 題：優先用 RAG
- 生成語氣：交給 OpenAI
- OpenAI 失敗：退回 fallback

### 人工轉接
- 情緒強烈
- 主動要求真人客服
- AI 不適合處理

## 你可以怎麼記這張架構圖

### 最短記法
- 前端進來
- handler 接住
- chat_service 做決策
- 需要知識就查 vector / FAQ
- 需要資料就查 SQLite
- 需要語言生成就打 OpenAI
- 最後結果再回前端

### 面試記法
- UI 層
- API 層
- Orchestration 層
- Service 層
- Repository 層
- Data 層

## 一句話結尾

### 這個架構最重要的特色
- 不是單一聊天機器人，而是把顧客對話、FAQ 檢索、訂單查詢、人工工單與後台操作整合成一條完整的客服系統資料流
