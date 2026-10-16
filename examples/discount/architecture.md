# ① 系統描述

## 技術棧
- Python 3.9 標準函式庫，不使用第三方套件。

## 架構約束

| 編號 | 約束 | 依據 | 驗證方式 |
|---|---|---|---|
| A1 | 只有一個模組 `src/discount.py`，不得新增其他模組。 | KISS | 審查 |
| A2 | `final_price` 是純函式：不讀寫檔案、不使用全域可變狀態、不印出內容。 | SRP | 審查 |

## 對外介面
```python
def final_price(amount: float, is_member: bool) -> float:
    ...
```
- 唯一對外函式。測試以 `from discount import final_price` 匯入。

## 技術決策
- 測試放在 `tests/test_discount.py`，使用標準函式庫 `unittest`。
- 執行方式：由流程依 `flow.config.json` 的 `test_command` 執行（AI 不直接執行）。
