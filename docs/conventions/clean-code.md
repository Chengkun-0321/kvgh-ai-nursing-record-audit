# Clean Code 規範

適用前後端所有程式碼。原則：**小函式、單一職責、名稱即文件**。

## 量化上限

| 項目 | 上限 | 工具強制 |
|---|---|---|
| 函式長度 | 30 個敘述（React 元件 150 行） | ruff `PLR0915`／eslint `max-lines-per-function` |
| 參數數量 | 4（超過改傳 Pydantic model／dataclass／物件） | ruff `PLR0913`／eslint `max-params` |
| 巢狀深度 | 2 層 | eslint `max-depth`／人工 |
| 循環複雜度 | 8 | ruff `C901`／eslint `complexity` |
| 分支數 | 8 | ruff `PLR0912` |
| 檔案長度 | 300 行 | eslint `max-lines`／人工 |

超過上限 = 該拆了，不是加 `noqa`／`eslint-disable`。確有必要時，須在同一行註明理由。

## 函式拆分

- 一個函式只做一件事，且只在**同一個抽象層級**
- 典型拆法：「取資料 → 判斷 → 組結果」分成獨立函式
- 用 early return（guard clause）取代巢狀 `if`
- 用函式名稱取代註解：需要註解解釋「這段在做什麼」時，就抽成函式

示意（邏輯為舉例，非實際規則設計）：

```python
# ❌ 取資料、判斷、組結果全擠在一起
async def evaluate(self, ctx: AuditContext) -> AuditFinding:
    missing = []
    for consultation in ctx.consultations:
        if consultation.consulted_at.date() == ctx.business_date:
            found = False
            for note in ctx.progress_notes:
                if consultation.department in note.content:
                    found = True
            if not found:
                missing.append(consultation)
    ...

# ✅ 每一步一個具名函式
async def evaluate(self, ctx: AuditContext) -> AuditFinding:
    consultations = _consultations_on(ctx.business_date, ctx.consultations)
    unrecorded = [c for c in consultations if not _is_recorded(c, ctx.progress_notes)]
    return _build_finding(unrecorded)
```

## 命名

| 對象 | Python | TypeScript |
|---|---|---|
| 變數、函式 | `snake_case` | `camelCase` |
| 類別、型別、元件 | `PascalCase` | `PascalCase` |
| 常數 | `UPPER_SNAKE_CASE` | `UPPER_SNAKE_CASE` |
| 檔名 | `snake_case.py` | 元件 `PascalCase.tsx`，其他 `camelCase.ts` |

- 領域名詞一律依 [glossary.md](../glossary.md)，同一概念全專案只用一個英文名
- 函式以動詞開頭：`load_audit_context`、`calculate_similarity`、`buildFinding`
- boolean 以 `is_` / `has_` / `should_`（TS：`is` / `has` / `should`）開頭
- 數值帶單位：`timeout_seconds`、`similarity_ratio`
- 不用無意義縮寫（`tmp`、`data2`、`res`）；glossary 列出的縮寫除外

## 禁止 magic number／magic string

- 門檻、次數、天數 → `Settings` 或模組常數，例：`COPY_CHECK_LOOKBACK_DAYS = 3`
- 尚未確定的值（如相似度門檻 80%／90%）**必須**可由設定調整
- 稽核必要要素清單（如入院經過五要素）→ 定義在該規則模組的常數，prompt 由程式注入，不在多處重複

## 錯誤處理

- 自訂例外繼承 `core/exceptions.py` 的 `AppError`，依情境細分（`LLMOutputError`、`IngestionValidationError`…）
- 禁止 `except Exception: pass`；捕捉就要處理，或加上下文後重新拋出（`raise … from e`）
- 外部依賴（LLM、中繼站）失敗時，要落到明確狀態（`NEEDS_REVIEW`、匯入失敗紀錄），**不得偽裝成功**
- 例外訊息不得含病患識別資料
- 前端：API 錯誤顯示繁中友善訊息，不顯示 stack trace

## 註解與文件

- 一律繁中；註解寫 **why**（為什麼這樣做），不寫 what
- Python public 函式／類別寫 Google style docstring：

```python
def calculate_similarity(previous: str, current: str) -> float:
    """計算兩份護理紀錄的文字相似度。

    Args:
        previous: 前一日紀錄內文。
        current: 當日紀錄內文。

    Returns:
        0.0–1.0 的相似度比例。
    """
```

- TS 匯出的函式、hook 寫 JSDoc
- TODO 格式：`# TODO(待決): 說明`，對應根目錄 CLAUDE.md 的待決事項
- 不留註解掉的程式碼（ruff `ERA` 會擋）；刪掉，git 有歷史

## 型別

- Python：所有函式參數與回傳值都有 type hints，`mypy --strict` 必須通過；`Any` 只能出現在外部邊界且需註明原因
- TypeScript：`strict`，禁止 `any`
- 值物件優先不可變：`@dataclass(frozen=True)` 或 Pydantic `frozen=True`

## 避免過度設計

- 重複 3 次才抽象（Rule of Three）
- 不為假想需求預留擴充點；但下列是**已知需求**，必須從一開始就抽象：
  - DB：SQLite → PostgreSQL
  - 資料來源：假資料 → 中繼站
  - LLM：使用者可切換模型
