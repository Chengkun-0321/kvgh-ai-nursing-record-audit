# 前端規範（Next.js）

> 通用規範見根目錄 [CLAUDE.md](../CLAUDE.md) 與 [docs/conventions/](../docs/conventions/)。本檔只列前端專屬事項。

## 環境：套件只裝在 `frontend/node_modules`

- 套件管理只用 `npm`；禁用 `npm -g`、`yarn`、`pnpm`、`corepack enable`
- `frontend/.npmrc` 設定 `cache=.npm-cache`（相對於執行目錄），因此 **npm 指令一律在 `frontend/` 根目錄執行**
- CLI 一律用專案內版本：`npm run <script>` 或 `npx <tool>`
- 新增套件：`npm install --save-exact <pkg>`；`package-lock.json` 必須 commit

### 初始化（尚未執行）

於專案根目錄先在暫存目錄產生，再合併（保留既有 `CLAUDE.md`、`AGENTS.md`、`.npmrc`）：

```bash
npm_config_cache="$PWD/frontend/.npm-cache" npx create-next-app@latest frontend-init --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --skip-install --yes
```

```bash
rsync -a --ignore-existing frontend-init/ frontend/ && rm -rf frontend-init && cd frontend && npm install
```

完成後套用下方「工具設定」。

## 核准依賴（其餘需先詢問）

- 正式：`next`、`react`、`react-dom`、`motion`（Framer Motion 更名後的套件，`import { motion } from "motion/react"`）、`clsx`、`tailwind-merge`
- 開發：`typescript`、`tailwindcss`、`@tailwindcss/postcss`、`eslint`、`eslint-config-next`、`prettier`、`prettier-plugin-tailwindcss`、`openapi-typescript`
- 寫測試時：`vitest`、`@testing-library/react`、`@testing-library/jest-dom`、`jsdom`
- 未經同意不引入 SWR、TanStack Query、Redux、Zustand、UI 元件庫等

## 目錄（Next.js App Router 標準結構）

```
frontend/
├── public/
└── src/
    ├── app/              # 路由：layout.tsx、page.tsx、loading.tsx、error.tsx
    ├── components/
    │   ├── ui/           # 通用元件，無業務邏輯（Button、Card、Drawer、Badge…）
    │   └── …             # 業務元件（BedCard、PatientSummary、AuditFindingList…）
    ├── hooks/            # useXxx
    ├── lib/              # api client、utils（cn）、motion variants、constants
    └── types/            # 型別；api.ts 由 OpenAPI 產生，禁止手改
```

同一領域業務元件超過約 5 個時，可建子資料夾（如 `components/bed-board/`）。

## React / Next.js

- 預設 Server Component；需要 state、事件、瀏覽器 API、Framer Motion 時才加 `"use client"`，並把 client 範圍壓到葉節點
- 一檔一元件；元件檔名 PascalCase（`BedCard.tsx`），hooks `useXxx.ts`，其他 camelCase
- 除 Next.js 規定需 default export 的檔案（`page`、`layout`…）外，一律 named export
- Props 型別：`type BedCardProps = { … }`
- 元件只負責呈現；資料轉換、判斷邏輯抽到 hooks 或 `lib/`
- 元件 ≤ 150 行，超過就拆

## 資料存取

- 後端呼叫一律經 `src/lib/api/`，元件內不直接 `fetch` 後端 URL
- 後端位址：Server 端用 `API_BASE_URL`，Client 端用 `NEXT_PUBLIC_API_BASE_URL`
- API 型別：`npm run gen:api` 由 FastAPI `/openapi.json` 產生 `src/types/api.ts`；禁止手寫重複的 API 型別
- 後端 schema 變更後必須重新產生 `api.ts`

## TypeScript

- `strict: true` + `noUncheckedIndexedAccess: true`
- 禁用 `any`（用 `unknown` + 型別縮小）；非必要不用 `as`、`!`
- `Verdict` 等列舉使用 `api.ts` 產生的 union literal，不自行重定義

## Tailwind CSS（v4，CSS-first 設定）

- design token 定義在 `src/app/globals.css` 的 `@theme`，例：

```css
@theme {
  --color-verdict-pass: oklch(0.72 0.17 150);
  --color-verdict-warning: oklch(0.8 0.16 80);
  --color-verdict-error: oklch(0.63 0.22 25);
  --color-verdict-review: oklch(0.65 0.03 260);
}
```

- 禁止 inline `style`、禁止任意色碼（`bg-[#…]`）；顏色、陰影、光暈一律走 token
- 條件 class 用 `cn()`（`src/lib/utils.ts`，clsx + tailwind-merge）
- Verdict 呈現必須「顏色 + icon + 文字」，不可只靠顏色
- RWD：mobile-first，使用 `sm` / `md` / `lg` 斷點

## Framer Motion

- 只在 client component 使用
- variants、duration、easing 集中於 `src/lib/motion.ts`，元件內不各自定義數值
- 只動畫 `transform`、`opacity`；列表進出用 `AnimatePresence` / `layout`
- 根 layout 以 `<MotionConfig reducedMotion="user">` 尊重使用者的減少動態設定
- 動畫不可阻擋操作（Drawer 開關 ≤ 300ms）

## 無障礙

- 可點擊元素用 `<button>` / `<a>`，禁止 `div onClick`
- Drawer：可用 `Esc` 關閉；開啟時 focus 移入，關閉後還原
- 純圖示按鈕需繁中 `aria-label`

## 工具設定（初始化後套用）

`tsconfig.json` 的 `compilerOptions` 加上 `"noUncheckedIndexedAccess": true`。

`package.json` scripts 加上：

```json
{
  "typecheck": "tsc --noEmit",
  "format": "prettier --write .",
  "gen:api": "openapi-typescript http://localhost:8000/openapi.json -o src/types/api.ts"
}
```

`.prettierrc`：

```json
{ "plugins": ["prettier-plugin-tailwindcss"] }
```

`eslint.config.mjs` 追加：

```js
{
  rules: {
    "@typescript-eslint/no-explicit-any": "error",
    "no-console": ["warn", { allow: ["warn", "error"] }],
    "max-params": ["error", 4],
    "max-depth": ["error", 2],
    complexity: ["error", 8],
    "max-lines": ["error", { max: 300, skipBlankLines: true, skipComments: true }],
  },
},
{
  files: ["src/components/**/*.tsx", "src/app/**/*.tsx"],
  rules: { "max-lines-per-function": ["error", { max: 150, skipBlankLines: true, skipComments: true }] },
},
{
  files: ["src/lib/**/*.ts", "src/hooks/**/*.ts"],
  rules: { "max-lines-per-function": ["error", { max: 30, skipBlankLines: true, skipComments: true }] },
},
```

## 檢查

```bash
npm run lint && npm run typecheck
```
