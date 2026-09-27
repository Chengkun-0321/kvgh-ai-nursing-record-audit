import type { Sex } from "@/types/ward";

/** 病床圖片素材的年齡層分組。 */
export type AgeGroup = "young" | "middle" | "elder";

const MIDDLE_AGE_FROM_YEARS = 45;
const ELDER_AGE_FROM_YEARS = 65;
const MS_PER_DAY = 24 * 60 * 60 * 1000;

export const SEX_LABELS: Record<Sex, string> = { M: "男", F: "女" };

/** 依年齡決定病床圖片的年齡層。 */
export function getAgeGroup(ageYears: number): AgeGroup {
  if (ageYears >= ELDER_AGE_FROM_YEARS) {
    return "elder";
  }
  return ageYears >= MIDDLE_AGE_FROM_YEARS ? "middle" : "young";
}

/**
 * 計算住院天數（業務日期與入院日期相差的日數）。
 *
 * @param admissionDate 入院日期（YYYY-MM-DD）
 * @param businessDate 業務日期（YYYY-MM-DD）
 */
export function getLengthOfStayDays(
  admissionDate: string,
  businessDate: string,
): number {
  const admittedAt = Date.parse(`${admissionDate}T00:00:00Z`);
  const businessAt = Date.parse(`${businessDate}T00:00:00Z`);
  return Math.max(0, Math.round((businessAt - admittedAt) / MS_PER_DAY));
}
