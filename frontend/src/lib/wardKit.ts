import straightJson from "./wardKit.straight.json";
import tiltedJson from "./wardKit.tilted.json";

/**
 * 病房場景模組設定：前端版面與 Blender 產生器（scripts/blender/）共用的單一來源。
 * 每個視角一份設定（`wardKit.<視角>.json`），各自一套 GLB 模組與病床去背圖。
 *
 * - `modelDir`／`spriteDir`：GLB 與去背圖的網址目錄；`style` 決定 Blender 模組的擺設規則
 * - `view`：相機 yaw／pitch（度），由 calibrate_sprite.py 依病床去背圖校準；`pxPerMeter` 為 100% 縮放時每公尺像素
 * - `grid`：欄數上下限與目標畫面比例；`snapM` 為地磚尺寸，所有模組原點都落在其倍數上
 * - `bay`：床位空間（公尺）；`bedCenterM` 為床心到該排後緣的距離
 * - `edges`：左右走道、前緣與樓板剖面尺寸（公尺）
 * - `bedProxy`：Blender 投射床下陰影用的病床代理物尺寸（公尺）
 * - `sprite`：病床去背圖的像素尺寸、平面寬度（公尺）、床心錨點、床號標籤錨點、有內容的範圍
 * - `modules`／`decals`：`modelDir` 下的 GLB 檔名，由 build_ward_kit.py 產生
 */
export type WardKit = typeof tiltedJson;

export type WardViewId = "straight" | "tilted";

export const WARD_KITS: Record<WardViewId, WardKit> = {
  straight: straightJson,
  tilted: tiltedJson,
};

/** 預設正視角；斜視角保留於地圖控制列切換。 */
export const DEFAULT_WARD_VIEW: WardViewId = "straight";

export type KitModuleId = keyof WardKit["modules"];

/** 模組檔案網址；附版本號讓重新建置後瀏覽器不會沿用舊快取。 */
export function getKitAssetUrl(kit: WardKit, file: string): string {
  return `${kit.modelDir}/${file}?v=${kit.assetVersion}`;
}
