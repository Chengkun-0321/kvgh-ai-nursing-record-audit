import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { VERDICT_STYLES } from "@/lib/verdictStyles";
import type { Verdict } from "@/types/ward";

type VerdictIconProps = {
  verdict: Verdict;
  className?: string;
};

const GLYPH_PROPS = {
  className: "fill-none stroke-white",
  strokeWidth: 2.4,
  strokeLinecap: "round",
  strokeLinejoin: "round",
} as const;

const EXCLAMATION = (
  <>
    <path d="M12 7v6" {...GLYPH_PROPS} />
    <circle cx="12" cy="17" r="1.4" className="fill-white" />
  </>
);

// 形狀差異讓色弱使用者也能分辨：圓環／三角形／驚嘆號圓形／問號圓形
const ICON_SHAPES: Record<Verdict, ReactNode> = {
  PASS: (
    <>
      <circle cx="12" cy="12" r="11" className="fill-current" />
      <circle cx="12" cy="12" r="5" {...GLYPH_PROPS} strokeWidth={2.8} />
    </>
  ),
  WARNING: (
    <>
      <path
        d="M10.3 2.9a2 2 0 0 1 3.4 0l9 15.6a2 2 0 0 1-1.7 3H3a2 2 0 0 1-1.7-3z"
        className="fill-current"
      />
      <g transform="translate(0 1)">{EXCLAMATION}</g>
    </>
  ),
  ERROR: (
    <>
      <circle cx="12" cy="12" r="11" className="fill-current" />
      {EXCLAMATION}
    </>
  ),
  NEEDS_REVIEW: (
    <>
      <circle cx="12" cy="12" r="11" className="fill-current" />
      <path
        d="M9.3 9.3a2.8 2.8 0 1 1 4.1 2.5c-.8.4-1.4 1-1.4 1.9v.3"
        {...GLYPH_PROPS}
      />
      <circle cx="12" cy="17.2" r="1.4" className="fill-white" />
    </>
  ),
};

/** 稽核判定圖示；一律搭配文字使用，不可單獨以顏色表達狀態。 */
export function VerdictIcon({ verdict, className }: VerdictIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      className={cn("size-5 shrink-0", VERDICT_STYLES[verdict].icon, className)}
    >
      {ICON_SHAPES[verdict]}
    </svg>
  );
}
