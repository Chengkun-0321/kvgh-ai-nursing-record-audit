# Git 規範

## 分支

- `main`：穩定可執行
- 工作分支：`<type>/<英文 kebab-case 簡述>`，例：`feat/r06-consultation-rule`、`fix/ingestion-checksum`

## Commit message

格式：`<type>(<scope>): <繁中描述>`

| type | 用途 |
|---|---|
| `feat` | 新功能 |
| `fix` | 修 bug |
| `refactor` | 重構（行為不變） |
| `docs` | 文件 |
| `test` | 測試 |
| `chore` | 設定、依賴、雜項 |

scope：`backend`、`frontend`、`audit`、`llm`、`ingestion`、`db`、`docs`（可省略）

範例：

```
feat(audit): 新增 R06 會診紀錄稽核規則
fix(ingestion): 修正重複匯入時未比對 checksum
docs: 詞彙表新增轉入摘要
```

- 需要說明「為什麼」時，空一行後寫內文（繁中）
- 一個 commit 一個目的；model 變更與其 migration 放同一個 commit

## 禁止 commit

`.env`、API key、`backend/data/`、任何病患資料（含院方假資料）、`node_modules/`、`.venv/`

## AI 行為

- 只有使用者要求時才 commit／push
- 禁止 `push --force`、改寫已推送的歷史、修改 git config
