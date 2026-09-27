"use client";

import { motion } from "motion/react";
import { useId } from "react";

import { VerdictIcon } from "@/components/VerdictIcon";
import { SPRING_DEFAULT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import {
  VERDICT_LABELS,
  VERDICTS_BY_SEVERITY,
  type VerdictFilterValue,
} from "@/lib/verdict";
import type { Verdict } from "@/types/ward";

type WardStatusBarProps = {
  bedCounts: Record<Verdict, number>;
  value: VerdictFilterValue;
  onChange: (value: VerdictFilterValue) => void;
  className?: string;
};

/**
 * 各狀態床數統計（淺色液態玻璃），同時是篩選開關；再點一次已選取的項目即回到全部。
 * 選取底色以 spring 在項目間滑動。
 */
export function WardStatusBar({
  bedCounts,
  value,
  onChange,
  className,
}: WardStatusBarProps) {
  const indicatorLayoutId = useId();

  return (
    <div
      role="group"
      aria-label="依稽核狀態篩選病床"
      className={cn(
        "glass relative grid grid-cols-4 gap-1 rounded-card p-1.5 shadow-float",
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
              "relative flex min-h-11 pressable items-center gap-2 rounded-xl px-2 py-2 focus-ring disabled:opacity-40 sm:gap-3 sm:px-3",
              !isActive && "hover:bg-fill",
            )}
          >
            {isActive && (
              <motion.span
                layoutId={indicatorLayoutId}
                transition={SPRING_DEFAULT}
                aria-hidden="true"
                className="absolute inset-0 rounded-xl bg-fill-strong"
              />
            )}
            <VerdictIcon verdict={verdict} className="relative size-7" />
            <span className="relative flex flex-col items-start">
              <span className="text-title tabular-nums">{count}</span>
              <span
                className={cn(
                  "text-caption font-medium whitespace-nowrap @xl:text-footnote",
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
