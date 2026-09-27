# 前端 UI 設計規範

全前端採一致的 Apple 風格：工作區以程式繪製的暖色病房與寫實素材為底，功能層使用 iOS／macOS 液態玻璃材質。依據兩份專案內 skill：

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

| 類別     | Token                                                                                      | 用途                                                                                          |
| -------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| 字體     | `font-sans`                                                                                | 系統字優先（SF Pro／蘋方 → 思源黑體 → 微軟正黑體），不載入網路字型                            |
| 字級     | `text-large-title` / `title` / `headline` / `body` / `footnote` / `caption` / `tab`        | 已含行高、字距、字重；大字字距收緊、小字放寬                                                  |
| 介面色   | `canvas`、`surface`、`ink`、`ink-secondary`、`fill`、`fill-strong`、`separator`、`scrim`   | 背景、卡片、文字、控制項底色、分隔線、模態遮罩；`ink-secondary` 加深到疊在淺色玻璃上仍 ≥4.5:1 |
| 玻璃     | `glass`、`chrome`、`on-chrome`、`on-chrome-secondary`、`chrome-fill`、`chrome-fill-strong` | 卡片玻璃與結構層玻璃的底色、結構層上的文字、hover 與選取底色                                  |
| 場景     | `scene-*`（牆面、設備帶、燈光、地板、木紋、金屬、螢幕、隔簾、布面、陰影、環境光）          | 只給病房場景使用，元件 UI 不可引用                                                            |
| 主操作色 | `accent`（操作藍）、`accent-contrast`                                                      | 主要按鈕、focus 外框；與 `NEEDS_REVIEW` 分開定義，狀態以圖示、文字輔助辨識                    |
| 狀態色   | `verdict-{error,warning,review,pass}` 與 `-strong`                                         | 主色用於圖示；`-strong` 為白底 ≥4.5:1 的文字色                                                |
| 徽章     | `badge`                                                                                    | 待處理數字徽章（白字 ≥4.5:1）                                                                 |
| 圓角     | `rounded-card`（20px）、`rounded-panel`（28px）                                            | 卡片／清單、面板／sheet                                                                       |
| 陰影     | `shadow-card`、`shadow-float`、`shadow-room`、`shadow-lamp`                                | 一般卡片、浮動層（面板、狀態列、sheet）、病房模型、燈條光暈                                   |
| 尺寸     | `topbar`、`rail`、`sidebar`、`detail`                                                      | 頂列高度、側欄寬度（圖示列／完整）、詳情面板寬度                                              |

## 材質（液態玻璃）

| Utility        | 用途                                                         | 做法                                                                              |
| -------------- | ------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| `glass`        | 內容層：詳情大卡、病患頁內容面板                             | 白 0.89＋上緣光澤漸層＋`blur(30px) saturate(190%)`；`::before` 畫漸層邊緣高光     |
| `glass-chrome` | 結構層（深灰玻璃）：頂列、側欄、手機分頁列、狀態列、病房標籤 | 深灰 0.86＋`blur(32px)`；文字為 `on-chrome`（白），次要文字 `on-chrome-secondary` |

- 使用玻璃的元素本身必須有定位（`relative`／`sticky`／`absolute`／`fixed`），邊緣高光才會貼齊。
- **透明度動畫要做在玻璃元素本身**，不可做在祖先：祖先 `opacity < 1` 會讓 `backdrop-filter` 暫時失效，動畫結束時畫面會跳一下。
- 不可把玻璃疊在另一層玻璃上；玻璃內的清單、卡片、狀態膠囊改用實色 `surface`（淡色 tint 需先墊一層 `surface`）。
- 對比以最差背景驗證：淺色玻璃下墊純黑、深灰玻璃下墊純白，主文字與次要文字都 ≥ 4.5:1。調整玻璃不透明度或文字色時須重新驗證。
- `prefers-reduced-transparency` 改為實色；`prefers-contrast: more` 加實線外框（已寫在 utility 內）。
- 頂列底緣以漸層遮罩淡出（`mask-b-*`），大卡捲動區底緣同樣以遮罩淡出，不用 1px 分隔線。

## 病房場景（Blender 場景模組＋React Three Fiber）

技術選型見 [ADR 0003](../adr/0003-ward-scene-3d.md)。

- **組成**：
  - 場景由 Blender 產生的**場景模組**（`public/models/ward/*.glb`）依床數動態拼成。
  - 模組分為三類：床位空間（第 0 排靠後牆、其餘排靠床頭隔屏）、左右側走道（含後牆轉角與輪替擺設）、前緣剖面。
  - 病床與病人沿用去背圖，放在正對相機的平面上。
- **單一來源**：`frontend/src/lib/wardKit.json`，前端版面（`lib/wardLayout.ts`）與 Blender 產生器（`scripts/blender/`）共用。內容：
  - 模組尺寸，公尺；地磚 0.6 m，所有模組原點都落在其倍數上
  - 相機 yaw／pitch
  - 去背圖錨點
- **視角**：
  - 相機固定 yaw 13.7°、pitch 36.5°，由 `calibrate_sprite.py` 依病床去背圖校準。
  - 使用正交投影，只能平移、縮放，不能旋轉。改變視角必須重新生成去背圖並重新校準。
- **光影**：
  - 每個模組放在 4×3 的病房環境中，以 Cycles 從固定相機算圖，再把算圖結果「投影」回模型當貼圖。鄰居模組提供陰影與反光，但相機看不到它們。
  - 網頁端以無光照材質（`MeshBasicMaterial`、`flat`）直接顯示，所以看到的顏色、地板反光、柔和陰影都等於 Blender 算圖結果。
  - 場景不放燈光，也不用 HDRI。
- **床下陰影**：以病床代理物投在 shadow catcher 上算出，做成貼花，只放在有床的床位。空床位沒有殘影。
- **配色**：
  - Blender 材質色取自 `globals.css` 的 `--color-scene-*`（`kit/palette.py`），色調依概念圖取樣。
  - 裝飾物不使用稽核狀態的高彩度色。
  - 場景靜態，不做循環動畫。
- **避免遮擋**：相機略朝左看，高物件的投影會往左後方延伸。因此：
  - 監視器、床頭櫃放在床的左側；點滴架、陪病椅放右側。
  - 左側牆做全高，右側牆只做矮牆。
- **效能**：
  - 同一模組以 `InstancedMesh` 一次繪製；`frameloop="demand"`，只在相機移動或淡化時重繪；DPR 最多 2。
  - three.js 以 `next/dynamic`（`ssr: false`）拆成獨立 chunk。
- **內網**：不得從 CDN 載入任何資源，包括 HDRI、Draco decoder 與字型；GLB 內嵌 WebP 貼圖，不用 Draco。
- **降級**：沒有 WebGL（`failIfMajorPerformanceCaveat`）或場景載入失敗時，改用 2D 病床清單（`WardBedGrid`＋`BedCard`）。開發時可用 `?scene=2d` 檢查。

### 重新產生場景模組

在專案根目錄執行（Blender 為使用者已安裝的應用程式，不另裝套件）。

1. 視角校準：輸出疊圖供人工檢查，加 `--write` 寫回 wardKit.json。

   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python frontend/scripts/blender/calibrate_sprite.py -- <輸出資料夾>
   ```

2. 建置所有模組：可加 `--only baySpine bedShadow` 只建置指定模組。

   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python frontend/scripts/blender/build_ward_kit.py
   ```

3. 預覽組裝：`--source glb` 的結果與網頁相同；同時另存 `.cache/preview/ward-preview.blend`。

   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python frontend/scripts/blender/preview_ward.py -- --beds 10 --source glb --out <輸出.png>
   ```

修改模組後要重新建置，並把 `wardKit.json` 的 `assetVersion` 加 1，讓瀏覽器重新下載。

## 病房地圖

- `WardMapViewport` 分成三層，樣式在 `ward-scene.css`：
  - 底層：3D 場景 canvas，不接收指標事件。
  - 可移動的世界層：DOM 病床按鈕與床號標籤。
  - 固定層：標題、狀態列、詳情卡、縮放控制。
- `WardMapController` 以 Web Animations 移動世界層，並在同一幀透過 camera channel 設定 3D 相機、立即 `advance()`，所以平移時 DOM 標籤與 3D 畫面不會錯位。
- 預設視野讓整個病房放進可用範圍，最大 100%。縮放範圍 50–200%；滾輪以游標為錨點縮放，按住拖曳平移，雙指同時縮放／平移。Ctrl／Command 保留瀏覽器原生縮放。
- 超過 6px 視為拖曳，不開啟病床；雙指與取消的手勢亦不選床。常數集中在 `lib/wardMap.ts`。
- **版面只依床數決定**（`getWardGrid`：接近目標畫面比例、空床位最少）：
  - 整個病房是一個大空間，床由後排往前、每排由左往右排列。
  - 視窗寬度、篩選、縮放、開卡都不會重新排床；篩選只淡化不符合的床（3D 去背圖與標籤同步淡化）。
- 床號標籤以 `--map-scale` 反向縮放，字級不隨地圖縮放。縮放低於 75% 時只顯示圖示與床號，判定文字仍在 `aria-label` 與狀態列圖例中。
- 方向鍵移動、加減鍵縮放、0／Home 重設。Tab 聚焦病床時平移到可視區，避開固定標題、狀態列與詳情卡。
- 地圖使用 `overflow: clip`，避免瀏覽器自動捲動聚焦元素而偏移相機。座標、尺寸與 CSS 變數都以 Web Animations 寫入（`useMapKeyframe`），不使用 React inline style。
- 點床開詳情；再點同一床、按 X、Esc 或點背景可關閉。拖曳、縮放與篩選時詳情保留。桌機開卡時僅平移選中床位；手機使用模態 sheet。

## 元件模式

| 模式       | 規則                                                                                                                                                                                                                                                 |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 床號標籤   | 白色膠囊＋VerdictIcon＋床號＋判定文字（PASS 不顯示文字），位於床頭上方；選取中以操作藍外框標示，病床範圍出現選取框（`layoutId` 滑動）                                                                                                                |
| 狀態列     | 結構層玻璃；各 Verdict 床數，同時是篩選開關（`aria-pressed`，再點一次回到全部），選取底色（實色白膠囊）以 spring 滑動                                                                                                                                |
| 分段控制器 | `components/ui/SegmentedControl`；指示器以 spring 滑動；停用項目以 `disabledHint` 標示                                                                                                                                                               |
| 清單       | 實色 `surface` 卡片＋`divide-separator`                                                                                                                                                                                                              |
| 主要按鈕   | `rounded-full bg-accent text-accent-contrast`，高度 ≥ 44px，加上 `pressable` 與 `focus-ring`                                                                                                                                                         |
| 詳情大卡   | 桌機右側：**開頁不顯示，點選病床才浮現**；淺色玻璃、不加遮罩（不打斷操作）；地圖平移讓選中床位保持可見。X、Esc、再點同一床、點大卡與病床／狀態列以外的地方皆可關閉，以 X／Esc 關閉時焦點回到該床。高度固定、內容捲動，「進入病人個人頁面」固定在底部 |
| 模態 sheet | 手機詳情（點選病床開啟）：原生 `<dialog>`＋40% 黑遮罩；由下進、往下退；可拖曳把手關閉                                                                                                                                                                |

## 動態

- 參數集中在 `frontend/src/lib/motion.ts`，元件不自訂數值。
- 預設使用臨界阻尼 spring（`bounce: 0`），約 0.3–0.35 秒到位；只有帶動量的手勢才允許回彈。
- 動畫必須可中斷，並從目前的位置繼續；拖曳放手後，退場動畫要延續手指的速度。
- Sheet 是否關閉，依「目前位移＋動量投影」判斷（`shouldDismissSheet`），輕甩一下也能關閉。
- 只對 `transform` 和 `opacity` 做動畫。首屏資料不做進場淡入；3D 場景無法 SSR，在模型載入後直接出現（不淡入），DOM 病床按鈕在此之前即可操作。
- 詳情大卡以 `PANEL_MOTION`（opacity＋`x`＋`scale` 0.96→1）「浮現」，退場反向；`AnimatePresence` 管理右側浮層進出。
- 地圖跟隨手勢直接更新 transform；固定功能層不參與地圖縮放，文字與控制大小保持可讀。
- `MotionConfig reducedMotion="user"`：減少動態時，位移動畫只保留淡入淡出；床位 CSS hover／選取過渡同時停用，手動縮放仍可操作。

## 圖示

- 使用 Phosphor（`@phosphor-icons/react`），一律從 `components/ui/icons.ts` 引用；新增圖示時在該檔以 `dist/ssr/<Name>` 逐檔匯出。
- 一般狀態用 `regular`，選取中改用 `fill`；同一層級不可混用線條與實心。
- 圖示一律加 `aria-hidden="true"`；只有圖示的按鈕要附繁中 `aria-label`。
- Verdict 狀態圖示使用自繪的 `VerdictIcon`（實心形狀可區分：圓環／三角形／驚嘆號／問號）。

## 病床素材

- 路徑：`frontend/public/images/beds/bed-{m|f}-{young|middle|elder}-{pass|warning|error|review}.webp`，共 24 張。病房環境由 Blender 場景模組組成（見「病房場景」），病床與病人沿用素材。
- 畫布 480×580，背景透明，所有素材的床頭對齊同一高度。
- 依病患性別、年齡層（< 45、45–64、≥ 65 歲）與最嚴重判定選用（`lib/bedSprites.ts`）。
- 光暈已繪入素材：無光為 PASS、黃色為 WARNING、紅色為 ERROR、藍色為 NEEDS_REVIEW。
- 來源是使用者自行生成的 2×4 拼版圖。裁切時保留病床本體（含亮起的燈條），外圍光暈則依病床輪廓重新生成，避免相鄰床的光暈互相重疊。圖片僅為裝飾，不代表實際病患外觀。

## 補充素材

- `public/images/scene/ward-floor.webp`：GPT Image 生成的地板材質，只用於工作區背景（`.ambient-corridor`）；3D 場景的地磚由 Blender 程序材質產生。
- `public/images/patients/patient-{m|f}-{young|middle|elder}.webp`：六款生成的人物近景，用於詳情卡，顯示「示意影像」，不代表真實病患外觀。

## 交付前檢查

- 內文對比 ≥ 4.5:1（大字 ≥ 3:1）；不可只靠顏色表達狀態。
- 可互動元素的觸控區 ≥ 44×44px，並有可見的 `focus-ring`；Tab 順序與畫面順序一致。
- 停用狀態使用 `disabled` 或 `aria-disabled`，並明顯淡化。
- 不使用 emoji 當圖示；圖示來自同一圖示家族。
- 驗證 0／1／10／40／100 床；在 375、1024、1440 寬度下檢查版面（桌機含大卡開啟狀態）；確認內容不被固定列遮住，並避開 safe area。
- 以模擬方式檢查 `prefers-reduced-motion`、`prefers-reduced-transparency`、`prefers-contrast`。
- 3D 場景：`?scene=2d` 與停用 WebGL 時改用 2D 清單；100 床平移順暢；Network 面板只有同源請求（無 CDN）。

## Skill 查詢指令

在專案根目錄執行（使用系統內建的 `python3`，不另外安裝）：

```bash
python3 .claude/skill/ui-ux-pro-max/scripts/search.py "<關鍵字>" --domain ux
```

```bash
python3 .claude/skill/ui-ux-pro-max/scripts/search.py "<關鍵字>" --stack nextjs
```
