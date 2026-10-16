# 測試規範

**測試不強制**，由開發當下判斷；但既有測試必須保持通過。以下為撰寫時的約定。

## 建議優先補測試的地方

- 稽核規則的純邏輯部分（`rule` engine、hybrid 的程式篩選）
- 資料匯入的 schema 驗證與正規化
- gateway 的輸出解析與 hallucination guard

## 後端（pytest）

- 位置：`backend/tests/`，目錄結構對應 `app/`，檔名 `test_<module>.py`
- 函式命名描述情境與預期：`test_consultation_without_note_returns_warning`
- async 測試直接寫 `async def`（`asyncio_mode = "auto"`）
- DB：使用 `sqlite+aiosqlite:///:memory:`
- LLM：一律 mock gateway，測試不得發出任何網路請求

## 前端（Vitest + React Testing Library）

- 位置：`frontend/tests/`，目錄結構對應 `src/`，檔名 `*.test.ts(x)`，以 `@/` 匯入被測模組（測試與程式分開目錄，規格驅動流程才能隔離 coder 與測試角色，見 [spec-flow.md](spec-flow.md)）
- 測使用者可見行為（文字、角色、互動），不測實作細節

## 共通

- AAA 結構：Arrange → Act → Assert，以空行分隔
- fixture 必須完全虛構，放 `backend/tests/fixtures/`

## 準確率評估（與單元測試分開）

- 位置：`backend/evaluation/`，手動執行（會呼叫真實 LLM、產生費用）
- 以護理長標註的 golden set 為 ground truth，輸出各規則 precision／recall／F1 與誤報案例
- 評估結果記錄使用的 model 與 prompt_version
