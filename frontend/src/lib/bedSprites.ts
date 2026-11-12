import type {
  BedBoardStatus,
  BedStatus,
  PatientSummary,
} from "@/lib/api/wards";
import type { components } from "@/types/api";

import { DEFAULT_WARD_VIEW, WARD_KITS, type WardKit } from "./wardKit";

type Sex = components["schemas"]["Sex"];
type AgeGroup = components["schemas"]["AgeGroup"];

/** 2D 病床卡片（不支援 WebGL 時）沿用預設視角的素材。 */
const CARD_SPRITE_KIT = WARD_KITS[DEFAULT_WARD_VIEW];

/** 2D 病床卡片的素材畫布尺寸（px）；所有素材的床頭對齊同一高度，數值與 3D 場景共用 wardKit.<視角>.json。 */
export const BED_CARD_SPRITE_SIZE = {
  width: CARD_SPRITE_KIT.sprite.widthPx,
  height: CARD_SPRITE_KIT.sprite.heightPx,
};

const SEX_SEGMENTS: Record<Sex, string> = { M: "m", F: "f" };

// 院方資料沒有性別與年齡時使用的素材；圖片僅為裝飾，不代表實際病患外觀
const FALLBACK_SEX: Sex = "M";
const FALLBACK_AGE_GROUP: AgeGroup = "middle";

// 光暈已繪製在素材中：無光＝PASS／尚未稽核、黃＝WARNING、紅＝ERROR、藍＝NEEDS_REVIEW
const STATUS_SEGMENTS: Record<BedBoardStatus, string> = {
  PASS: "pass",
  NOT_AUDITED: "pass",
  WARNING: "warning",
  ERROR: "error",
  NEEDS_REVIEW: "review",
};

function spriteSegments(patient: PatientSummary): [string, string] {
  return [
    SEX_SEGMENTS[patient.sex ?? FALLBACK_SEX],
    patient.age_group ?? FALLBACK_AGE_GROUP,
  ];
}

/**
 * 依病患性別、年齡層與病床狀態選擇病床圖片；每個視角各有一套素材（`spriteDir`）。
 * 圖片僅為裝飾，不代表實際病患外觀。
 */
export function getBedSpriteSrc(
  bed: BedStatus,
  kit: WardKit = CARD_SPRITE_KIT,
): string {
  const segments = [
    ...spriteSegments(bed.patient),
    STATUS_SEGMENTS[bed.status],
  ];
  return `${kit.spriteDir}/bed-${segments.join("-")}.webp`;
}

/**
 * 各床的去背圖網址，以及去重後的清單（相同圖片只載入一次）。
 * 3D 場景與預載共用此函式：R3F 以整個陣列作為快取 key，兩邊順序必須一致。
 */
export function getBedSpriteSources(beds: readonly BedStatus[], kit: WardKit) {
  const sources = beds.map((bed) => getBedSpriteSrc(bed, kit));
  return { sources, uniqueSources: [...new Set(sources)] };
}

/**
 * 生成的示意近景僅依性別與年齡層選圖，不代表實際病患外觀；
 * 院方資料沒有性別或年齡層時回傳 `null`，不顯示近景。
 */
export function getPatientPortraitSrc(patient: PatientSummary): string | null {
  if (!patient.sex || !patient.age_group) {
    return null;
  }
  return `/images/patients/patient-${spriteSegments(patient).join("-")}.webp`;
}
