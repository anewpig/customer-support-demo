# SupportOS AI Customer Support Demo

![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![SQLite](https://img.shields.io/badge/database-sqlite-0f766e)
![Chroma](https://img.shields.io/badge/vector_store-chroma-2563eb)
![Status](https://img.shields.io/badge/status-demo_project-111827)

一個可實際部署的 AI 智慧客服 demo，包含顧客端聊天介面、內部客服操作台、RAG、訂單查詢、工單流程與登入權限。

## 給面試官的最快開啟方式

這個專案建議使用 `Python 3.11`。

1. 建立並啟用虛擬環境

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

2. 安裝套件

```bash
pip install -r requirements.txt
```

3. 複製環境變數檔

```bash
cp .env.example .env
```

4. 打開 `.env`，把下面這行改成自己的 OpenAI API key

```env
OPENAI_API_KEY=your_openai_api_key
```

也就是說，請把 `your_openai_api_key` 換成自己的 key。若不更換，OpenAI 問答與 embedding 不會正常工作。

5. 啟動專案

```bash
python server.py
```

或直接用虛擬環境的 Python：

```bash
./.venv/bin/python server.py
```

6. 打開頁面

- 顧客頁：[http://127.0.0.1:8000](http://127.0.0.1:8000)
- 登入頁：[http://127.0.0.1:8000/login.html](http://127.0.0.1:8000/login.html)

7. 預設後台帳密

- Username: `123456`
- Password: `654321`

注意：
- 建議不要直接用系統的 `python3 server.py`
- 請優先用 `.venv` 啟動，避免 Python 版本差異造成 SSL 或 OpenAI 連線問題

## Demo 重點

- 顧客頁與內部客服頁分離
- OpenAI Responses API 多輪對話
- FAQ data cleaning + RAG 檢索
- Chroma / JSON fallback 向量儲存
- SQLite 持久化 FAQ、訂單、對話、session
- 訂單驗證流程
- 人工客服工單流轉
- AI 工單摘要與建議回覆
- FAQ 缺口分析
- 後台 OpenAI runtime / 額度異常提示

## 介面

- 顧客頁：`/`
- 內部登入頁：`/login.html`
- 客服操作台：`/admin.html`

## 技術架構

### Backend

- Python `http.server`
- SQLite
- OpenAI Responses API
- OpenAI Embeddings
- Chroma

### Frontend

- HTML / CSS / Vanilla JavaScript

### Project Structure

```text
.
├── app/
│   ├── config.py
│   ├── server.py
│   ├── repositories/
│   ├── services/
│   └── web/
├── static/
│   ├── index.html
│   ├── admin.html
│   ├── login.html
│   ├── customer.js
│   ├── admin.js
│   ├── login.js
│   └── styles.css
├── data/
├── tests/
├── server.py
└── README.md
```

## 主要流程

1. 顧客在前台輸入問題
2. 後端先做 intent 判斷
3. 依需求查 FAQ、訂單或 session 歷史
4. FAQ 相關問題先走 RAG 檢索
5. 將問題、歷史與檢索結果送給 OpenAI
6. 若需人工處理，建立 handoff 工單
7. 內部頁可查看工單、聊天紀錄、訂單、FAQ 缺口與 AI 建議回覆

## 快速開始

### 1. 建議 Python 版本

- `Python 3.11`

如果你的電腦有多個 Python 版本，建議先確認：

```bash
python3.11 --version
```

### 2. 建立虛擬環境

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python --version
```

### 3. 安裝套件

```bash
pip install -r requirements.txt
```

如果要開發或跑 lint / coverage：

```bash
pip install -r requirements-dev.txt
```

### 4. 建立 `.env`

可直接複製 `.env.example`：

```bash
cp .env.example .env
```

接著請打開 `.env`，把 `OPENAI_API_KEY` 改成你自己的 key。

範例：

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
PORT=8000

ADMIN_USERNAME=123456
ADMIN_PASSWORD=654321
```

如果你沒有把 `your_openai_api_key` 換成自己的 key，系統雖然可以開啟，但 OpenAI 回覆與 embedding 會失敗或退回 fallback。

### 5. 啟動

```bash
python server.py
```

打開：

- [http://127.0.0.1:8000](http://127.0.0.1:8000)
- [http://127.0.0.1:8000/login.html](http://127.0.0.1:8000/login.html)

如果要換埠：

```bash
PORT=8766 python server.py
```

## 預設帳密

如果 `.env` 沒有覆蓋，預設為：

- Username: `123456`
- Password: `654321`

## OpenAI 模式

有設定 `OPENAI_API_KEY` 時：

- 對話回覆走 OpenAI Responses API
- 向量索引可走 OpenAI Embeddings

沒設定時：

- 自動退回本地 fallback 回覆

## 後台功能

- 待人工處理工單
- 工單狀態 / 指派 / 備註
- 聊天紀錄與 session 明細
- AI 工單摘要
- AI 建議回覆一鍵複製
- FAQ 缺口分析
- 訂單列表與展開明細
- OpenAI runtime 狀態卡

## 資料存放

- `data/app.db`：SQLite 主資料庫
- `data/orders.json`：範例訂單 seed
- `data/faq.json`：FAQ seed
- `data/chroma_db/`：Chroma 持久化資料
- `data/vector_store.json`：JSON vector fallback

## 測試

執行測試：

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

目前已補：

- service tests
- repository tests
- handler tests
- vector store tests

更多說明可看 [TESTING.md](TESTING.md)。

## Lint / Format / Coverage

```bash
make lint
make format
make coverage
```

或使用：

```bash
pre-commit install
pre-commit run --all-files
```

## 部署

這個專案已附：

- `render.yaml`
- `nixpacks.toml`
- `Dockerfile`

可直接部署到：

- Render
- Railway
- Docker

## Roadmap

- Streaming 回覆
- 更正式的通知系統
- PostgreSQL / 雲端向量資料庫
- 客服 SLA / 優先級
- 操作紀錄與審計
