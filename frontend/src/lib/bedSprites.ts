import type { BedStatus, PatientSummary, Sex, Verdict } from "@/types/ward";

import { getAgeGroup } from "./patient";
import { getWorstVerdict } from "./verdict";
import { DEFAULT_WARD_VIEW, WARD_KITS, type WardKit } from "./wardKit";

/** 2D 病床卡片（不支援 WebGL 時）沿用預設視角的素材。 */
const CARD_SPRITE_KIT = WARD_KITS[DEFAULT_WARD_VIEW];

/** 2D 病床卡片的素材畫布尺寸（px）；所有素材的床頭對齊同一高度，數值與 3D 場景共用 wardKit.<視角>.json。 */
export const BED_CARD_SPRITE_SIZE = {
  width: CARD_SPRITE_KIT.sprite.widthPx,
  height: CARD_SPRITE_KIT.sprite.heightPx,
};

const SEX_SEGMENTS: Record<Sex, string> = { M: "m", F: "f" };

// 光暈已繪製在素材中：無光＝PASS、黃＝WARNING、紅＝ERROR、藍＝NEEDS_REVIEW
const VERDICT_SEGMENTS: Record<Verdict, string> = {
  PASS: "pass",
  WARNING: "warning",
  ERROR: "error",
  NEEDS_REVIEW: "review",
};

/**
 * 依病患性別、年齡層與最嚴重判定選擇病床圖片；每個視角各有一套素材（`spriteDir`）。
 * 圖片僅為裝飾，不代表實際病患外觀。
 */
export function getBedSpriteSrc(
  patient: PatientSummary,
  verdict: Verdict,
  kit: WardKit = CARD_SPRITE_KIT,
): string {
  const segments = [
    SEX_SEGMENTS[patient.sex],
    getAgeGroup(patient.ageYears),
    VERDICT_SEGMENTS[verdict],
  ];
  return `${kit.spriteDir}/bed-${segments.join("-")}.webp`;
}

/**
 * 各床的去背圖網址，以及去重後的清單（相同圖片只載入一次）。
 * 3D 場景與預載共用此函式：R3F 以整個陣列作為快取 key，兩邊順序必須一致。
 */
export function getBedSpriteSources(beds: readonly BedStatus[], kit: WardKit) {
  const sources = beds.map((bed) =>
    getBedSpriteSrc(bed.patient, getWorstVerdict(bed.findings), kit),
  );
  return { sources, uniqueSources: [...new Set(sources)] };
}

/** 生成的示意近景僅依性別與年齡層選圖，不代表實際病患外觀。 */
export function getPatientPortraitSrc(patient: PatientSummary): string {
  return `/images/patients/patient-${SEX_SEGMENTS[patient.sex]}-${getAgeGroup(patient.ageYears)}.webp`;
}
