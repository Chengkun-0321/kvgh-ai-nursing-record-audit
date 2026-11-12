import type { BedBoardStatus } from "@/lib/api/wards";

type VerdictStyle = {
  /** 圖示主色 */
  icon: string;
  /** 白底可讀的深色文字 */
  text: string;
  /** 淡色底，用於選取中的狀態列項目與詳情標頭 */
  tint: string;
};

// class 字串需完整寫出，Tailwind 才能在建置時掃描到
export const VERDICT_STYLES: Record<BedBoardStatus, VerdictStyle> = {
  ERROR: {
    icon: "text-verdict-error",
    text: "text-verdict-error-strong",
    tint: "bg-verdict-error/12",
  },
  WARNING: {
    icon: "text-verdict-warning",
    text: "text-verdict-warning-strong",
    tint: "bg-verdict-warning/18",
  },
  NEEDS_REVIEW: {
    icon: "text-verdict-review",
    text: "text-verdict-review-strong",
    tint: "bg-verdict-review/12",
  },
  PASS: {
    icon: "text-verdict-pass",
    text: "text-verdict-pass-strong",
    tint: "bg-verdict-pass/12",
  },
  NOT_AUDITED: {
    icon: "text-verdict-unaudited",
    text: "text-verdict-unaudited-strong",
    tint: "bg-verdict-unaudited/12",
  },
};
