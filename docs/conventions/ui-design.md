# 前端 UI 設計規範

全前端採一致的 Apple 風格：首頁以鋪滿整個視窗的暖色病房場景與寫實素材為底，側欄、使用者膠囊等功能層都是疊在場景上的 iOS／macOS 液態玻璃材質（桌機外框見 [ADR 0005](../adr/0005-floating-glass-shell.md)）。依據兩份專案內 skill：

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

| 類別     | Token                                                                                    | 用途                                                                                               |
| -------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 字體     | `font-sans`                                                                              | 系統字優先（SF Pro／蘋方 → 思源黑體 → 微軟正黑體），不載入網路字型                                 |
| 字級     | `text-large-title` / `title` / `headline` / `body` / `footnote` / `caption` / `tab`      | 已含行高、字距、字重；大字字距收緊、小字放寬                                                       |
| 介面色   | `canvas`、`surface`、`ink`、`ink-secondary`、`fill`、`fill-strong`、`separator`、`scrim` | 背景、卡片、文字、控制項底色、分隔線、模態遮罩；`ink-secondary` 加深到疊在淺色玻璃上仍 ≥4.5:1      |
| 玻璃     | `glass`                                                                                  | 淺色液態玻璃底色（側欄、使用者膠囊、手機頂列與分頁列、標題、狀態列、縮放控制、詳情卡共用）         |
| 場景     | `scene-*`（牆面、設備帶、燈光、地板、木紋、金屬、螢幕、隔簾、布面、陰影、環境光、地坪）  | 只給病房場景使用，元件 UI 不可引用；`scene-apron` 為病房外的地坪（滿版舞台底色）                   |
| 主操作色 | `accent`（操作藍）、`accent-contrast`                                                    | 主要按鈕、focus 外框；與 `NEEDS_REVIEW` 分開定義，狀態以圖示、文字輔助辨識                         |
| 狀態色   | `verdict-{error,warning,review,pass}` 與 `-strong`                                       | 主色用於圖示；`-strong` 為白底 ≥4.5:1 的文字色                                                     |
| 徽章     | `badge`                                                                                  | 待處理數字徽章（白字 ≥4.5:1）                                                                      |
| 圓角     | `rounded-card`（20px）、`rounded-panel`（28px）                                          | 卡片／清單、面板／sheet                                                                            |
| 陰影     | `shadow-card`、`shadow-float`、`shadow-room`、`shadow-lamp`                              | 一般卡片、浮動層（面板、狀態列、sheet）、病房模型、燈條光暈                                        |
| 尺寸     | `topbar`、`toolbar`、`rail`、`sidebar`、`detail`                                         | 手機頂列高度、桌機頂部工具列列高（詳情卡與病患頁由此往下）、側欄寬度（圖示列／完整）、詳情面板寬度 |

## 材質（液態玻璃）

| Utility | 用途                                                                                                           | 做法                                                                                          |
| ------- | -------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `glass` | 所有浮在畫面上的功能層：滿高浮動側欄、右上使用者膠囊、手機頂列與分頁列、病房標題卡、狀態列、縮放控制、詳情大卡 | 白 0.76（透出場景暖色）＋上緣光澤漸層＋`blur(30px) saturate(190%)`；`::before` 畫漸層邊緣高光 |

- 使用玻璃的元素本身必須有定位（`relative`／`sticky`／`absolute`／`fixed`），邊緣高光才會貼齊。
- **透明度動畫要做在玻璃元素本身**，不可做在祖先：祖先 `opacity < 1` 會讓 `backdrop-filter` 暫時失效，動畫結束時畫面會跳一下。
- 不可把玻璃疊在另一層玻璃上；玻璃內的清單、卡片、狀態膠囊改用實色 `surface`（淡色 tint 需先墊一層 `surface`）。
- 對比以最差背景驗證：玻璃下墊純黑，主文字與次要文字都 ≥ 4.5:1（目前 ink 約 9.5:1、ink-secondary 約 5.1:1）。調整玻璃不透明度或文字色時須重新驗證。verdict `-strong` 文字色只放在實色 `surface` 上。
- `prefers-reduced-transparency` 改為實色；`prefers-contrast: more` 加實線外框（已寫在 utility 內）。
- 桌機沒有頂列：系統標誌放在側欄最上方，時間、待處理數與使用者放在右上角膠囊（`AppStatusCapsule`）；側欄、標題卡與膠囊對齊同一條上緣，浮動層之間與視窗邊緣的間距一律 1rem。
- 手機頂列底緣以漸層遮罩淡出（`mask-b-*`），大卡捲動區底緣同樣以遮罩淡出，不用 1px 分隔線。

## 病房場景（Blender 場景模組＋React Three Fiber）

技術選型見 [ADR 0003](../adr/0003-ward-scene-3d.md)；正視角與滿版見 [ADR 0004](../adr/0004-ward-straight-view.md)。

- **兩個視角**：預設**正視**（yaw 0°、pitch 60°），可在地圖控制列切換為**斜視**（原版面，yaw 13.7°、pitch 36.5°）。
  - 每個視角各有一份設定檔（`frontend/src/lib/wardKit.<straight|tilted>.json`）、一套 GLB 與一套病床去背圖，互不影響。
  - 設定檔的 `style` 決定 Blender 模組擺設：`leftLook`（斜視）或 `symmetric`（正視）。
- **組成**：
  - 場景由 Blender 產生的**場景模組**依床數動態拼成：正視在 `public/models/ward-straight/`，斜視在 `public/models/ward/`。
  - 模組分為三類：床位空間（第 0 排靠後牆、其餘排靠床頭隔屏）、左右側走道（含後牆轉角與輪替擺設）、前緣剖面。
  - 病床與病人沿用去背圖，放在正對相機的平面上。
- **單一來源**：各視角的 `wardKit.<視角>.json`，前端版面（`lib/wardLayout.ts`）、投影（`lib/wardProjection.ts`）與 Blender 產生器（`scripts/blender/`）共用。內容：
  - 模組尺寸，公尺；地磚 0.6 m，所有模組原點都落在其倍數上
  - 相機 yaw／pitch
  - 去背圖錨點、GLB 與去背圖目錄（`modelDir`、`spriteDir`）
  - 床下陰影代理物尺寸（`bedProxy`）
- **視角**：
  - 相機角度由 `calibrate_sprite.py` 依病床去背圖校準。斜視由去背圖斜率推算 yaw／pitch；正視（yaw 0）斜率公式無解，且生成圖不是嚴格的正交投影，所以 pitch 由校準檔指定（依床尾板正面與腳輪比例目測），只擬合縮放與錨點。
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
- **避免遮擋**：
  - 斜視相機略朝左看，高物件的投影會往左後方延伸。因此監視器、床頭櫃放在床的左側，點滴架、陪病椅放右側；左側牆做全高，右側牆只做矮牆。
  - 正視時高物件只往正後方投影、落在床頭牆上，沿用同一左右配置。側牆正對相機的面看不到，左右都做矮牆。平面隔簾會變成一條線，改為收攏在床頭端的布褶。前緣為低矮剖面牆，不建樓板。
- **效能**：
  - 同一模組以 `InstancedMesh` 一次繪製；`frameloop="demand"`，只在相機移動或淡化時重繪；DPR 最多 2。
  - three.js 以 `next/dynamic`（`ssr: false`）拆成獨立 chunk。
- **內網**：不得從 CDN 載入任何資源，包括 HDRI、Draco decoder 與字型；GLB 內嵌 WebP 貼圖，不用 Draco。
- **降級**：沒有 WebGL（`failIfMajorPerformanceCaveat`）或場景載入失敗時，改用 2D 病床清單（`WardBedGrid`＋`BedCard`）。開發時可用 `?scene=2d` 檢查。

### 重新產生場景模組

在專案根目錄執行（Blender 為使用者已安裝的應用程式，不另裝套件）。所有腳本都可加 `--view straight|tilted` 選擇視角，預設 straight；輸出目錄、算圖快取（`.cache/renders/<視角>/`）、校準檔（`sprite_calibration.<視角>.json`）都依視角分開。

1. 視角校準：輸出疊圖供人工檢查，加 `--write` 寫回該視角的設定檔。

   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python frontend/scripts/blender/calibrate_sprite.py -- <輸出資料夾> --view straight
   ```

2. 建置所有模組：可加 `--only baySpine bedShadow` 只建置指定模組。

   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python frontend/scripts/blender/build_ward_kit.py -- --view straight
   ```

3. 預覽組裝：`--source glb` 的結果與網頁相同；同時另存 `.cache/preview/ward-preview-<視角>.blend`。

   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python frontend/scripts/blender/preview_ward.py -- --view straight --beds 10 --source glb --out <輸出.png>
   ```

修改模組後要重新建置，並把該視角設定檔的 `assetVersion` 加 1，讓瀏覽器重新下載。修改兩個視角共用的道具時，兩個視角都要重建。

## 病房地圖

- **滿版與安全區**：
  - `.ward-stage` 固定鋪滿整個視窗，側欄與使用者膠囊（`z-30`）、手機頂列與分頁列疊在場景上。
  - `.ward-safe` 以 CSS 扣掉這些外框：手機上方扣頂列、底部扣分頁列；lg 以上上方不扣（場景直達上緣），左側扣側欄卡片寬加 1rem。
  - `.ward-safe` 的 padding 是病房適配留白（手機 0.75rem、lg 2rem）：病房四周留有地坪，不貼外框。
  - 病房外（含外框後方）露出舞台底色 `scene-apron`（靜態暖灰加柔光），不露出白底。
- `WardMapViewport` 分成三層，樣式在 `ward-scene.css`：
  - 底層：3D 場景 canvas（透明背景），不接收指標事件。
  - 可移動的世界層：DOM 病床按鈕與床號標籤。
  - 固定層：標題、狀態列、詳情卡、縮放與視角控制，都放在 `.ward-safe` 內（容器不接收指標事件，可互動的子元素加 `pointer-events-auto`）。
- `WardMapController` 以 Web Animations 移動世界層，並在同一幀透過 camera channel 設定 3D 相機、立即 `advance()`，所以平移時 DOM 標籤與 3D 畫面不會錯位。
- 最小倍率＝整個病房剛好完整放進「安全區扣掉適配留白」的範圍（不扣標題、狀態列，它們疊在病房上），不能再縮小；最大 200%（床很少時不低於最小倍率）。預設視野為最小倍率、置中於該範圍；窄螢幕完整顯示會過小，初始至少 50%。
- 扣掉留白的安全區永遠落在病房範圍內：放大後病房邊緣最多拖到留白處，放不滿的軸置中，病房可滑到外框玻璃下方；開詳情卡時扣掉卡片寬度（與病房保留 `panelGapPx` 間距），右側病床仍可拖到卡片左側，關卡後重新夾限。量測在 `lib/wardMapBounds.ts`（`measureMapArea`）。
- **視角切換**：縮放控制右側的「正視／斜視」（`ViewToggle`，`aria-pressed`，選取底色以 spring 滑動）。切換時不重新掛載地圖、焦點留在按鈕上；版面與相機改用該視角的設定檔，視野重設為完整顯示。
- 滾輪以游標為錨點縮放，按住拖曳平移，雙指同時縮放／平移。Ctrl／Command 保留瀏覽器原生縮放。
- 超過 6px 視為拖曳，不開啟病床；雙指與取消的手勢亦不選床。常數集中在 `lib/wardMap.ts`。
- **版面只依床數決定**（`getWardGrid`：接近目標畫面比例、空床位最少）：
  - 整個病房是一個大空間，床由後排往前、每排由左往右排列。
  - 視窗寬度、篩選、縮放、開卡都不會重新排床；篩選只淡化不符合的床（3D 去背圖與標籤同步淡化）。
- 床號標籤以 `--map-scale` 反向縮放，字級不隨地圖縮放。縮放低於 75% 時只顯示圖示與床號，判定文字仍在 `aria-label` 與狀態列圖例中。
- 方向鍵移動、加減鍵縮放、0／Home 重設。Tab 聚焦病床時平移到可視區，避開固定標題、狀態列與詳情卡。
- 地圖使用 `overflow: clip`，避免瀏覽器自動捲動聚焦元素而偏移相機。座標、尺寸與 CSS 變數都以 Web Animations 寫入（`useMapKeyframe`），不使用 React inline style。
- 點床開詳情；再點同一床、按 X、Esc 或點背景可關閉。拖曳、縮放與篩選時詳情保留。桌機開卡時僅平移選中床位；手機使用模態 sheet。

## 元件模式

| 模式       | 規則                                                                                                                                                                                                                                                                                                        |
| ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 床號標籤   | 白色膠囊＋VerdictIcon＋床號＋判定文字（PASS 不顯示文字），位於床頭上方；選取中以操作藍外框標示，病床範圍出現選取框（`layoutId` 滑動）                                                                                                                                                                       |
| 狀態列     | 結構層玻璃；各 Verdict 床數，同時是篩選開關（`aria-pressed`，再點一次回到全部），選取底色（實色白膠囊）以 spring 滑動                                                                                                                                                                                       |
| 分段控制器 | `components/ui/SegmentedControl`；指示器以 spring 滑動；停用項目以 `disabledHint` 標示                                                                                                                                                                                                                      |
| 清單       | 實色 `surface` 卡片＋`divide-separator`                                                                                                                                                                                                                                                                     |
| 主要按鈕   | `rounded-full bg-accent text-accent-contrast`，高度 ≥ 44px，加上 `pressable` 與 `focus-ring`                                                                                                                                                                                                                |
| 詳情大卡   | 桌機右側：**開頁不顯示，點選病床才浮現**；由 `--spacing-toolbar` 以下開始，不遮住右上使用者膠囊；淺色玻璃、不加遮罩（不打斷操作）；地圖平移讓選中床位保持可見。X、Esc、再點同一床、點大卡與病床／狀態列以外的地方皆可關閉，以 X／Esc 關閉時焦點回到該床。高度固定、內容捲動，「進入病人個人頁面」固定在底部 |
| 模態 sheet | 手機詳情（點選病床開啟）：原生 `<dialog>`＋40% 黑遮罩；由下進、往下退；可拖曳把手關閉                                                                                                                                                                                                                       |

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

- 路徑：`frontend/public/images/<目錄>/bed-{m|f}-{young|middle|elder}-{pass|warning|error|review}.webp`，每個視角 24 張。病房環境由 Blender 場景模組組成（見「病房場景」），病床與病人沿用素材。
  - 正視：`beds-straight/`，畫布 440×580；2D 病床卡片（`BedCard`）也使用這套。
  - 斜視：`beds/`，畫布 480×580。
- 背景透明，同一套素材的床頭對齊同一高度。
- 依病患性別、年齡層（< 45、45–64、≥ 65 歲）與最嚴重判定選用（`lib/bedSprites.ts`）。
- 光暈已繪入素材：無光為 PASS、黃色為 WARNING、紅色為 ERROR、藍色為 NEEDS_REVIEW。
- 來源是使用者自行生成的 2×4 拼版圖（每視角 3 張，依序為高齡、中年、青年；上列男、下列女；欄依序為 PASS／WARNING／ERROR／NEEDS_REVIEW）。裁切時保留病床本體（含亮起的燈條），外圍光暈則依病床輪廓重新生成，避免相鄰床的光暈互相重疊。裁切腳本為一次性工具，不進版控。圖片僅為裝飾，不代表實際病患外觀。

## 補充素材

- `public/images/scene/ward-floor.webp`：GPT Image 生成的地板材質，只用於 2D 備援病房（`.ward-room`）；3D 場景的地磚由 Blender 程序材質產生。
- `public/images/patients/patient-{m|f}-{young|middle|elder}.webp`：六款生成的人物近景，用於詳情卡，顯示「示意影像」，不代表真實病患外觀。

## 交付前檢查

- 內文對比 ≥ 4.5:1（大字 ≥ 3:1）；不可只靠顏色表達狀態。
- 可互動元素的觸控區 ≥ 44×44px，並有可見的 `focus-ring`；Tab 順序與畫面順序一致。
- 停用狀態使用 `disabled` 或 `aria-disabled`，並明顯淡化。
- 不使用 emoji 當圖示；圖示來自同一圖示家族。
- 驗證 0／1／10／40／100 床；在 375、1024、1440 寬度下檢查版面（桌機含大卡開啟狀態）；確認內容不被固定列遮住，並避開 safe area。
- 以模擬方式檢查 `prefers-reduced-motion`、`prefers-reduced-transparency`、`prefers-contrast`。
- 3D 場景：正視與斜視都要檢查；`?scene=2d` 與停用 WebGL 時改用 2D 清單；100 床平移順暢；Network 面板只有同源請求（無 CDN）。

## Skill 查詢指令

在專案根目錄執行（使用系統內建的 `python3`，不另外安裝）：

```bash
python3 .claude/skill/ui-ux-pro-max/scripts/search.py "<關鍵字>" --domain ux
```

```bash
python3 .claude/skill/ui-ux-pro-max/scripts/search.py "<關鍵字>" --stack nextjs
```
