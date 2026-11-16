import type { BedStatus } from "@/lib/api/wards";

type BedLabelSource = Pick<
  BedStatus,
  "bed_code" | "summary_text" | "audit_progress_text"
>;

/**
 * 病床的無障礙名稱：床號、判定摘要、稽核進度。三段文字皆由後端產生，前端只串接，不自行計算。
 * 進度不以視覺文字呈現於地圖標籤，因此必須放在 aria-label，否則螢幕閱讀器使用者聽不到覆蓋範圍。
 */
export function getBedAriaLabel(bed: BedLabelSource): string {
  return `${bed.bed_code}，${bed.summary_text}，${bed.audit_progress_text}`;
}
