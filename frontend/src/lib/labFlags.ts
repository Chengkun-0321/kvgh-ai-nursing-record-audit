import type { AbnormalFlag } from "@/lib/api/rawData";

type FlagStyle = { symbol: string; label: string; className: string };

// 異常方向一律「符號＋文字（aria）＋顏色」，不單靠顏色；正常值不加強調
export const LAB_FLAG_STYLES: Record<AbnormalFlag, FlagStyle> = {
  high: {
    symbol: "↑",
    label: "偏高",
    className: "font-semibold text-verdict-error-strong",
  },
  low: {
    symbol: "↓",
    label: "偏低",
    className: "font-semibold text-verdict-review-strong",
  },
  abnormal: {
    symbol: "＊",
    label: "異常",
    className: "font-semibold text-verdict-warning-strong",
  },
  normal: { symbol: "", label: "", className: "text-ink" },
};
