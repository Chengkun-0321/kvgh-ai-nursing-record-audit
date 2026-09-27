# 前端 UI 設計規範

全前端採一致的 Apple 風格。依據兩份專案內 skill：

- `.claude/skill/apple-design/SKILL.md`：動態（spring、可中斷、速度延續）、材質與層次、字體、設計原則
- `.claude/skill/ui-ux-pro-max/`：無障礙與互動檢查清單、圖示規範、Next.js 準則（查詢指令見文末）

token 實作在 `frontend/src/app/globals.css` 的 `@theme`；元件只用語意 token，禁止任意色碼與 inline style。

## 原則

| 原則           | 本專案的做法                                                                                 |
| -------------- | -------------------------------------------------------------------------------------------- |
| 清楚層級       | 最重要的資訊最醒目：病床狀態光暈 → 床號標籤 → 摘要；次要文字用 `ink-secondary`               |
| 顏色不單獨表意 | Verdict 一律「顏色＋圖示形狀＋文字」                                                         |
| 可預期         | 看起來可點的一定能點；尚未實作的功能以停用狀態保留位置並標示「即將推出」，不做成沒反應的按鈕 |
| 即時回饋       | 按下（pointer-down）當下就縮小回饋（`pressable`），不等放開                                  |
| 所在位置       | 導覽標示目前頁（`aria-current`），子頁提供「‹ 上一層」返回                                   |
| 克制           | 每個畫面最多 1–2 個重點動畫；不做循環呼吸等長時間動畫                                        |

## Token

| 類別     | Token                                                                                    | 用途                                                                               |
| -------- | ---------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| 字體     | `font-sans`                                                                              | 系統字優先（SF Pro／蘋方 → 思源黑體 → 微軟正黑體），不載入網路字型                 |
| 字級     | `text-large-title` / `title` / `headline` / `body` / `footnote` / `caption` / `tab`      | 已含行高、字距、字重；大字字距收緊、小字放寬                                       |
| 介面色   | `canvas`、`surface`、`ink`、`ink-secondary`、`fill`、`fill-strong`、`separator`、`scrim` | 背景、卡片、文字、控制項底色、分隔線、模態遮罩                                     |
| 主操作色 | `accent`（石墨黑）、`accent-contrast`                                                    | 主要按鈕、選取中的標籤、focus 外框。藍色已是 `NEEDS_REVIEW` 狀態色，不可當主操作色 |
| 狀態色   | `verdict-{error,warning,review,pass}` 與 `-strong`                                       | 主色用於圖示；`-strong` 為白底 ≥4.5:1 的文字色                                     |
| 徽章     | `badge`                                                                                  | 待處理數字徽章（白字 ≥4.5:1）                                                      |
| 圓角     | `rounded-card`（20px）、`rounded-panel`（28px）                                          | 卡片／清單、面板／sheet                                                            |
| 陰影     | `shadow-card`、`shadow-float`                                                            | 一般卡片、浮動層（面板、狀態列、sheet）                                            |
| 尺寸     | `topbar`、`rail`、`sidebar`、`detail`                                                    | 頂列高度、側欄寬度（圖示列／完整）、詳情面板寬度                                   |

## 材質

- `glass`：浮在內容上的功能層（頂列、底部分頁列、狀態列、詳情面板）。
- `glass-heavy`：分隔結構區塊（側欄）。
- 不可把淺色半透明層疊在另一層半透明層上；半透明層內的清單、卡片改用實色 `surface`。
- 兩者在 `prefers-reduced-transparency` 下改為實色，在 `prefers-contrast: more` 下加實線外框（已寫在 utility 內）。
- 頂列底緣以漸層遮罩淡出（`mask-b-*`），不用 1px 分隔線。

## 元件模式

| 模式       | 規則                                                                                         |
| ---------- | -------------------------------------------------------------------------------------------- |
| 床號標籤   | 白色膠囊＋VerdictIcon；選取中改為石墨黑底白字                                                |
| 狀態列     | 各 Verdict 床數，同時是篩選開關（`aria-pressed`，再點一次回到全部）                          |
| 分段控制器 | `components/ui/SegmentedControl`；指示器以 spring 滑動；停用項目以 `disabledHint` 標示       |
| 清單       | 實色 `surface` 卡片＋`divide-separator`                                                      |
| 主要按鈕   | `rounded-full bg-accent text-accent-contrast`，高度 ≥ 44px，加上 `pressable` 與 `focus-ring` |
| 並行面板   | 桌機右側詳情：半透明材質，不加遮罩（不打斷操作）                                             |
| 模態 sheet | 手機詳情：原生 `<dialog>`＋40% 黑遮罩；由下進、往下退；可拖曳把手關閉                        |

## 動態

- 參數集中在 `frontend/src/lib/motion.ts`，元件不自訂數值。
- 預設使用臨界阻尼 spring（`bounce: 0`），約 0.3–0.35 秒到位；只有帶動量的手勢才允許回彈。
- 動畫必須可中斷，並從目前的位置繼續；拖曳放手後，退場動畫要延續手指的速度。
- Sheet 是否關閉，依「目前位移＋動量投影」判斷（`shouldDismissSheet`），輕甩一下也能關閉。
- 只對 `transform` 和 `opacity` 做動畫。首屏資料不做進場淡入。
- `MotionConfig reducedMotion="user"`：減少動態時，位移動畫只保留淡入淡出。

## 圖示

- 使用 Phosphor（`@phosphor-icons/react`），一律從 `components/ui/icons.ts` 引用；新增圖示時在該檔以 `dist/ssr/<Name>` 逐檔匯出。
- 一般狀態用 `regular`，選取中改用 `fill`；同一層級不可混用線條與實心。
- 圖示一律加 `aria-hidden="true"`；只有圖示的按鈕要附繁中 `aria-label`。
- Verdict 狀態圖示使用自繪的 `VerdictIcon`（實心形狀可區分：圓環／三角形／驚嘆號／問號）。

## 病床素材

- 路徑：`frontend/public/images/beds/bed-{m|f}-{young|middle|elder}-{pass|warning|error|review}.webp`，共 24 張。
- 畫布 480×580，背景透明，所有素材的床頭對齊同一高度。
- 依病患性別、年齡層（< 45、45–64、≥ 65 歲）與最嚴重判定選用（`lib/bedSprites.ts`）。
- 光暈已繪入素材：無光為 PASS、黃色為 WARNING、紅色為 ERROR、藍色為 NEEDS_REVIEW。
- 來源是使用者自行生成的 2×4 拼版圖。裁切時保留病床本體（含亮起的燈條），外圍光暈則依病床輪廓重新生成，避免相鄰床的光暈互相重疊。圖片僅為裝飾，不代表實際病患外觀。

## 交付前檢查

- 內文對比 ≥ 4.5:1（大字 ≥ 3:1）；不可只靠顏色表達狀態。
- 可互動元素的觸控區 ≥ 44×44px，並有可見的 `focus-ring`；Tab 順序與畫面順序一致。
- 停用狀態使用 `disabled` 或 `aria-disabled`，並明顯淡化。
- 不使用 emoji 當圖示；圖示來自同一圖示家族。
- 在 375、1024、1440 寬度下檢查版面；確認內容不被固定列遮住，並避開 safe area。
- 以模擬方式檢查 `prefers-reduced-motion`、`prefers-reduced-transparency`、`prefers-contrast`。

## Skill 查詢指令

在專案根目錄執行（使用系統內建的 `python3`，不另外安裝）：

```bash
python3 .claude/skill/ui-ux-pro-max/scripts/search.py "<關鍵字>" --domain ux
```

```bash
python3 .claude/skill/ui-ux-pro-max/scripts/search.py "<關鍵字>" --stack nextjs
```
