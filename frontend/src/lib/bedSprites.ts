import type { PatientSummary, Sex, Verdict } from "@/types/ward";

import { getAgeGroup } from "./patient";

const BED_SPRITE_DIR = "/images/beds";

/** 病床素材畫布尺寸（px）；所有素材的床頭對齊同一高度。 */
export const BED_SPRITE_SIZE = { width: 480, height: 580 } as const;

const SEX_SEGMENTS: Record<Sex, string> = { M: "m", F: "f" };

// 光暈已繪製在素材中：無光＝PASS、黃＝WARNING、紅＝ERROR、藍＝NEEDS_REVIEW
const VERDICT_SEGMENTS: Record<Verdict, string> = {
  PASS: "pass",
  WARNING: "warning",
  ERROR: "error",
  NEEDS_REVIEW: "review",
};

/**
 * 依病患性別、年齡層與最嚴重判定選擇病床圖片。
 * 圖片僅為裝飾，不代表實際病患外觀。
 */
export function getBedSpriteSrc(
  patient: PatientSummary,
  verdict: Verdict,
): string {
  const segments = [
    SEX_SEGMENTS[patient.sex],
    getAgeGroup(patient.ageYears),
    VERDICT_SEGMENTS[verdict],
  ];
  return `${BED_SPRITE_DIR}/bed-${segments.join("-")}.webp`;
}
