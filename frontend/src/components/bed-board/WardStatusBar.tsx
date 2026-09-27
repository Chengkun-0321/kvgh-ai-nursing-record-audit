"use client";

import { VerdictIcon } from "@/components/VerdictIcon";
import { cn } from "@/lib/utils";
import {
  VERDICT_LABELS,
  VERDICTS_BY_SEVERITY,
  type VerdictFilterValue,
} from "@/lib/verdict";
import { VERDICT_STYLES } from "@/lib/verdictStyles";
import type { Verdict } from "@/types/ward";

type WardStatusBarProps = {
  bedCounts: Record<Verdict, number>;
  value: VerdictFilterValue;
  onChange: (value: VerdictFilterValue) => void;
  className?: string;
};

/** 各狀態床數統計，同時是篩選開關；再點一次已選取的項目即回到全部。 */
export function WardStatusBar({
  bedCounts,
  value,
  onChange,
  className,
}: WardStatusBarProps) {
  return (
    <div
      role="group"
      aria-label="依稽核狀態篩選病床"
      className={cn(
        "grid grid-cols-4 gap-1 rounded-card glass p-1.5 shadow-float",
        className,
      )}
    >
      {VERDICTS_BY_SEVERITY.map((verdict) => {
        const isActive = verdict === value;
        const count = bedCounts[verdict];
        return (
          <button
            key={verdict}
            type="button"
            aria-pressed={isActive}
            aria-label={`${VERDICT_LABELS[verdict]} ${count} 床`}
            disabled={count === 0 && !isActive}
            onClick={() => onChange(isActive ? "ALL" : verdict)}
            className={cn(
              "flex min-h-11 pressable flex-col items-center gap-1 rounded-2xl px-2 py-2 focus-ring disabled:opacity-40 @xl:flex-row @xl:gap-3 @xl:px-3",
              isActive ? VERDICT_STYLES[verdict].tint : "hover:bg-fill",
            )}
          >
            <VerdictIcon verdict={verdict} className="size-6 @xl:size-7" />
            <span className="flex flex-col items-center @xl:items-start">
              <span className="text-title tabular-nums">{count}</span>
              <span
                className={cn(
                  "text-caption whitespace-nowrap @xl:text-footnote",
                  isActive ? "text-ink" : "text-ink-secondary",
                )}
              >
                {VERDICT_LABELS[verdict]}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
