# ① 系統描述

折扣計算：前端表單輸入金額與是否為會員，呼叫後端 API 取得應付金額。

## 技術棧
- 後端：Python 3.10 以上、FastAPI、Pydantic v2
- 前端：React 18、TypeScript、Vite
- 測試：後端 pytest + FastAPI `TestClient`；前端 Vitest + React Testing Library + jsdom

## 分層與模組

```
frontend/src/components/  →  frontend/src/api/   ──HTTP──▶  backend/app/routers/  →  backend/app/services/  →  backend/app/domain/
（畫面）                     （唯一呼叫 fetch）              （HTTP、輸入驗證）         （組合折扣規則）           （折扣規則，純邏輯）
```

| 檔案 | 職責 |
|---|---|
| `backend/app/main.py` | 建立 `app`，掛上 router |
| `backend/app/routers/discount.py` | `POST /api/discount`，Pydantic 驗證輸入 |
| `backend/app/services/discount_service.py` | `DiscountService`、`get_discount_service()` |
| `backend/app/domain/strategies.py` | `DiscountStrategy` 介面與各折扣實作 |
| `frontend/src/api/discountApi.ts` | `calculateDiscount()` |
| `frontend/src/components/DiscountForm.tsx` | 表單元件 |
| `frontend/src/App.tsx`、`frontend/src/main.tsx` | 組裝：把 `calculateDiscount` 傳給 `DiscountForm` |

## 架構約束（Design Patterns／SOLID）

| 編號 | 約束 | 依據 | 驗證方式 |
|---|---|---|---|
| A1 | 每一種折扣（R1 滿額、R2 會員、R3 下限）各是一個實作 `DiscountStrategy` 的類別，定義在 `backend/app/domain/strategies.py`。 | Strategy | 審查 |
| A2 | `DiscountService` 依建構時傳入的 strategy 清單依序套用，本身不含 `if` 判斷折扣種類；新增折扣只需新增類別並加入 `get_discount_service()` 的清單。 | OCP | 審查 |
| A3 | `backend/app/routers/` 下的檔案不得 import `app.domain`；router 透過 `Depends(get_discount_service)` 取得 service。 | DIP | 測試 |
| A4 | `backend/app/domain/` 下的檔案不得 import `fastapi` 或 `pydantic`。 | SRP | 測試 |
| A5 | `frontend/src/components/` 下的檔案不得出現 `fetch(`；只有 `frontend/src/api/` 可以呼叫 `fetch`。 | SRP | 測試 |
| A6 | `DiscountForm` 不直接 import `api/`，而是由 props 的 `calculate` 取得計算函式。 | DIP | 測試 |

## 對外介面

後端：
```python
# backend/app/domain/strategies.py
class DiscountStrategy(Protocol):
    def apply(self, amount: float, is_member: bool) -> float: ...

# backend/app/services/discount_service.py
class DiscountService:
    def __init__(self, strategies: list[DiscountStrategy]): ...
    def final_price(self, amount: float, is_member: bool) -> float: ...
def get_discount_service() -> DiscountService: ...
```
- 測試以 `from app.main import app` 取得 FastAPI 應用（在 `backend/` 目錄執行 pytest）。

前端：
```ts
// frontend/src/api/discountApi.ts
export async function calculateDiscount(amount: number, isMember: boolean): Promise<number>
// frontend/src/components/DiscountForm.tsx
export function DiscountForm(props: { calculate: (amount: number, isMember: boolean) => Promise<number> }): JSX.Element
```
- 測試以 `import { DiscountForm } from '../src/components/DiscountForm'` 匯入。

## 技術決策（由 /spec-draft 決定，人看過即可）
- coder 產生 `frontend/package.json`、`vite.config.ts`（開發時 `/api` 代理到 `http://localhost:8000`）、`tsconfig.json`（`"jsx": "react-jsx"`）、`index.html`、`backend/requirements.txt`。
- test-designer 產生 `frontend/vitest.config.ts`（`environment: 'jsdom'`）。
- 測試檔：後端 `backend/tests/`，前端 `frontend/tests/`。
- 允許的套件見 `flow.config.json` 的 `deps_check`。
- 執行方式：由流程依 `setup_command`、`test_command` 執行（AI 不直接執行）。
