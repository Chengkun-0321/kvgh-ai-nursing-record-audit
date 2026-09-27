# 前端規範（Next.js）

> 通用規範見根目錄 [CLAUDE.md](../CLAUDE.md) 與 [docs/conventions/](../docs/conventions/)。本檔只列前端專屬事項。
> UI 樣式、動畫、無障礙一律依 [ui-design.md](../docs/conventions/ui-design.md)（Apple 風格）。

## 環境：套件只裝在 `frontend/node_modules`

- 套件管理只用 `npm`；禁用 `npm -g`、`yarn`、`pnpm`、`corepack enable`
- `frontend/.npmrc` 設定 `cache=.npm-cache`（相對於執行目錄），因此 **npm 指令一律在 `frontend/` 根目錄執行**
- CLI 一律用專案內版本：`npm run <script>` 或 `npx <tool>`
- 新增套件：`npm install --save-exact <pkg>`；`package-lock.json` 必須 commit

### 初始化（已完成，保留供參考）

於專案根目錄先在暫存目錄產生，再合併（保留既有 `CLAUDE.md`、`AGENTS.md`、`.npmrc`）：

```bash
npm_config_cache="$PWD/frontend/.npm-cache" npx create-next-app@latest frontend-init --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --skip-install --yes
```

```bash
rsync -a --ignore-existing frontend-init/ frontend/ && rm -rf frontend-init && cd frontend && npm install
```

完成後套用下方「工具設定」。

### Next.js 16 注意事項

- API 與慣例可能與既有認知不同，撰寫前先查 `node_modules/next/dist/docs/`（例：`error.tsx` 的重試 prop 為 `retry`）
- `next.config.ts` 設 `agentRules: false`：本目錄 `AGENTS.md` 是本檔的 symlink，避免 `next dev` 自動寫入英文區塊

## 核准依賴（其餘需先詢問）

- 正式：`next`、`react`、`react-dom`、`motion`（Framer Motion 更名後的套件，`import { motion } from "motion/react"`）、`clsx`、`tailwind-merge`、`@phosphor-icons/react`（圖示，一律經 `src/components/ui/icons.ts` 引用）、`three`、`@react-three/fiber`（病房 3D 場景，見 [ADR 0003](../docs/adr/0003-ward-scene-3d.md)；`@react-three/drei` 已核准但目前不需要）
- 開發：`typescript`、`@types/node`、`@types/react`、`@types/react-dom`（create-next-app 預設）、`tailwindcss`、`@tailwindcss/postcss`、`eslint`、`eslint-config-next`、`prettier`、`prettier-plugin-tailwindcss`、`openapi-typescript`、`@types/three`
- 寫測試時：`vitest`（已安裝 4.x；npm 10 解析其選用 peer 會出錯，安裝時需加 `--legacy-peer-deps`）、`@testing-library/react`、`@testing-library/jest-dom`、`jsdom`
- 3D 資源一律放在本專案（`public/models/`），不得從 CDN 載入 HDRI、Draco decoder 等（醫院內網）
- 未經同意不引入 SWR、TanStack Query、Redux、Zustand、UI 元件庫等

## 目錄（Next.js App Router 標準結構）

```
frontend/
├── public/
│   ├── images/           # beds 病床、patients 示意近景、scene 地板材質；見 ui-design.md
│   └── models/ward/      # 病房場景模組 GLB（由 scripts/blender 產生，勿手改）
├── scripts/
│   └── blender/          # Blender 場景模組產生器（Python，於 Blender 內執行）
└── src/
    ├── app/              # 路由；登入後頁面放 (workspace)/，共用工作區外框
    ├── components/
    │   ├── ui/           # 通用元件，無業務邏輯（SegmentedControl、icons…）
    │   ├── app-shell/    # 工作區外框：頂列、側欄、底部分頁列
    │   ├── ward-scene/   # 病房 3D 場景（R3F）、DOM 病床按鈕層、地圖控制與視窗
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

- design token 定義在 `src/app/globals.css` 的 `@theme`（清單與用途見 ui-design.md「Token」）；共用樣式以 `@utility` 定義（`glass`、`glass-chrome`、`focus-ring`、`pressable`、`scene-ambient`、`window-blinds`）
- 病房版面由 `lib/wardLayout.ts` 只依床數決定（與 `scripts/blender/kit/layout.py` 同規則），開卡／縮放／篩選不重新排床；投影與相機換算在 `lib/wardProjection.ts`，尺寸單一來源為 `lib/wardKit.json`。地圖樣式在 `src/app/ward-scene.css`，控制器與病床按鈕以 Web Animations 更新 transform 與 CSS 變數（`useMapKeyframe`）。
- 禁止 inline `style`、禁止任意色碼（`bg-[#…]`）；顏色、陰影、光暈一律走 token
- 條件 class 用 `cn()`（`src/lib/utils.ts`，clsx + tailwind-merge）
- Verdict 呈現必須「顏色 + icon + 文字」，不可只靠顏色
- RWD：mobile-first；`lg` 以上顯示側欄與右側詳情大卡（點選病床才出現），以下改用底部分頁列與 bottom sheet

## Framer Motion

- 只在 client component 使用
- variants、duration、easing 集中於 `src/lib/motion.ts`，元件內不各自定義數值
- 只動畫 `transform`、`opacity`；列表進出用 `AnimatePresence` / `layout`
- 根 layout 以 `<MotionConfig reducedMotion="user">` 尊重使用者的減少動態設定
- 預設臨界阻尼 spring（`SPRING_DEFAULT`），動畫可中斷、不阻擋操作；sheet 開關約 300ms
- 設了 `whileHover` 等 variant 標籤的元素不會繼承父層 `initial`／`animate`，需自行指定
- 首屏資料不做進場淡入，避免 JS 載入前內容不可見
- SSR 會輸出的日期時間一律經 `src/lib/format.ts`（`formatToParts` 自組字串）；直接 `Intl.format()` 在 Node 與瀏覽器的分隔字元不同，會造成 hydration 不符

## 無障礙

- 可點擊元素用 `<button>` / `<a>`，禁止 `div onClick`
- Bottom sheet 用原生 `<dialog>` 的 `showModal()`：Esc 關閉、背景 inert、關閉後焦點回到觸發元素
- 純圖示按鈕需繁中 `aria-label`；裝飾性圖示加 `aria-hidden="true"`
- 觸控區 ≥ 44×44px；互動元素加 `focus-ring`

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
{
  "plugins": ["prettier-plugin-tailwindcss"],
  "tailwindStylesheet": "./src/app/globals.css"
}
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
npm run lint && npm run typecheck && npm test
```
