import kitJson from "./wardKit.json";

/**
 * 病房場景模組設定：前端版面與 Blender 產生器（scripts/blender/）共用的單一來源。
 *
 * - `view`：相機 yaw／pitch（度），由 calibrate_sprite.py 依病床去背圖校準；`pxPerMeter` 為 100% 縮放時每公尺像素
 * - `grid`：欄數上下限與目標畫面比例；`snapM` 為地磚尺寸，所有模組原點都落在其倍數上
 * - `bay`：床位空間（公尺）；`bedCenterM` 為床心到該排後緣的距離
 * - `edges`：左右走道、前緣與樓板剖面尺寸（公尺）
 * - `sprite`：病床去背圖的像素尺寸、平面寬度（公尺）、床心錨點、床號標籤錨點、有內容的範圍
 * - `modules`／`decals`：`public/models/ward/` 下的 GLB 檔名，由 build_ward_kit.py 產生
 */
export type WardKit = typeof kitJson;

export const WARD_KIT: WardKit = kitJson;

export type KitModuleId = keyof WardKit["modules"];

const MODEL_DIR = "/models/ward";

/** 模組檔案網址；附版本號讓重新建置後瀏覽器不會沿用舊快取。 */
export function getKitAssetUrl(file: string): string {
  return `${MODEL_DIR}/${file}?v=${WARD_KIT.assetVersion}`;
}
