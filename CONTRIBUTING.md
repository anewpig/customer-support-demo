# Contributing Guide

## 目標

這份文件用來說明如何參與這個專案的開發與維護。

## 開發環境

### 安裝依賴

```bash
pip install -r requirements-dev.txt
```

### 啟動專案

```bash
python3 server.py
```

### 執行測試

```bash
make test
```

### 執行 coverage

```bash
make coverage
```

### 執行 lint

```bash
make lint
```

### 執行 format

```bash
make format
```

### 安裝 pre-commit

```bash
pre-commit install
```

## Branch 建議

- 功能開發：`feature/<name>`
- 修 bug：`fix/<name>`
- 重構：`refactor/<name>`
- 文件：`docs/<name>`

如果在 Codex / AI 分支上工作，也可以使用：

- `codex/<name>`

## Commit 建議

建議訊息清楚描述改動目的，例如：

- `feat: add sqlite repository for conversations`
- `fix: guard frontend when API is unavailable`
- `test: add vector store service coverage`
- `docs: update project structure guide`

## Pull Request 建議

PR 至少應包含：

- 這次改了什麼
- 為什麼要改
- 如何測試
- 是否有風險或相容性影響

## 開發原則

- 優先維持模組分層清楚
- 新功能盡量補測試
- 不要把商業邏輯塞回 `server.py`
- API、service、repository 儘量分開
- 與 OpenAI 或資料儲存相關的變更，優先考慮 fallback 行為

## 文件同步

如果修改下列內容，請同步更新文件：

- 專案結構：更新 [PROJECT_STRUCTURE_XMIND.md](/Users/zhuangcaizhen/Desktop/3:26面試/PROJECT_STRUCTURE_XMIND.md)
- 測試流程：更新 [TESTING.md](/Users/zhuangcaizhen/Desktop/3:26面試/TESTING.md)
- 啟動或部署流程：更新 [README.md](/Users/zhuangcaizhen/Desktop/3:26面試/README.md)
