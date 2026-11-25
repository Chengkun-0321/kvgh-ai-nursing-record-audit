import type { BedBoardStatus, RuleCell, RuleCellState } from "@/lib/api/wards";

// 只對應呈現樣式；執行狀態、判定、發現數與文字皆採用後端回應。
const CELL_VERDICTS: Record<RuleCellState, BedBoardStatus | null> = {
  RUNNING: null,
  PASS: "PASS",
  WARNING: "WARNING",
  NEEDS_REVIEW: "NEEDS_REVIEW",
  ERROR: "ERROR",
  FAILED: null,
  NOT_APPLICABLE: null,
  DATA_UNAVAILABLE: null,
  DAY_NOT_ENDED: null,
  NOT_AUDITED: "NOT_AUDITED",
};

/** 將後端格子轉成顯示用文字與圖示鍵；不依 verdict 或資料可用性推導狀態。 */
export function getRuleCellPresentation(cell: RuleCell) {
  return {
    verdict: CELL_VERDICTS[cell.state],
    text:
      cell.finding_count > 0
        ? `${cell.label} ${cell.finding_count}`
        : cell.label,
    isRunning: cell.state === "RUNNING",
  };
}
