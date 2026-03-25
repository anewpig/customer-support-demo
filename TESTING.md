# Testing Guide

## 測試目標

這個專案目前的測試分成四層：

- `Cleaning tests`
  驗證 FAQ data cleaning pipeline 是否正常
- `Repository tests`
  驗證 SQLite repository 的 FAQ / conversation / session 存取
- `Service tests`
  驗證 chat service 與 vector store service 的主流程
- `Handler tests`
  驗證 HTTP API 路由能正常回應

## 測試檔案

- [tests/test_cleaning_service.py](/Users/zhuangcaizhen/Desktop/3:26面試/tests/test_cleaning_service.py)
- [tests/test_sqlite_repository.py](/Users/zhuangcaizhen/Desktop/3:26面試/tests/test_sqlite_repository.py)
- [tests/test_chat_service.py](/Users/zhuangcaizhen/Desktop/3:26面試/tests/test_chat_service.py)
- [tests/test_vector_store_service.py](/Users/zhuangcaizhen/Desktop/3:26面試/tests/test_vector_store_service.py)
- [tests/test_handler.py](/Users/zhuangcaizhen/Desktop/3:26面試/tests/test_handler.py)

## 執行方式

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

### Coverage

```bash
coverage run -m unittest discover -s tests -p "test_*.py"
coverage report -m
```

或直接使用：

```bash
make coverage
```

### Lint / Format

```bash
ruff check .
black --check .
```

自動修正：

```bash
make format
```

### Pre-commit

安裝：

```bash
pip install -r requirements-dev.txt
pre-commit install
```

手動執行：

```bash
pre-commit run --all-files
```

## 目前涵蓋內容

### Data Cleaning
- normalize whitespace
- normalize text
- normalize keywords
- FAQ 去重
- keyword 去重

### SQLite Repository
- FAQ seed
- FAQ list / upsert
- conversation insert / list
- session get / upsert

### Chat Service
- fallback 回答流程
- ticket 寫入
- session 更新
- FAQ 更新邏輯

### Vector Store Service
- JSON 向量索引建立
- 向量相似度檢索
- usable vector index 判斷

### HTTP Handler
- `/healthz`
- `/api/status`
- `/api/chat`

## 設計原則

- 測試不依賴真實 OpenAI API
- 測試不依賴真實網路
- 測試不依賴真實 Chroma 服務
- 使用 fake service 讓測試穩定可重現

## 後續可補強

- FAQ API 新增 / 錯誤情境測試
- `/api/reindex` 測試
- 前端 E2E 測試
- GitHub Actions badge
