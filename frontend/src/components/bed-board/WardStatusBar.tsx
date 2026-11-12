"use client";

import { useId } from "react";

import { SelectionIndicator } from "@/components/ui/SelectionIndicator";
import { VerdictIcon } from "@/components/VerdictIcon";
import { cn } from "@/lib/utils";
import type { StatusCount } from "@/lib/api/wards";
import type { BedFilterValue } from "@/lib/verdict";

type WardStatusBarProps = {
  /** 各狀態床數，順序與名稱由後端決定 */
  statusCounts: readonly StatusCount[];
  value: BedFilterValue;
  onChange: (value: BedFilterValue) => void;
  className?: string;
};

/**
 * 各狀態床數統計（淺色液態玻璃），同時是篩選開關；再點一次已選取的項目即回到全部。
 * 選取底色以 spring 在項目間滑動。
 */
export function WardStatusBar({
  statusCounts,
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
        "glass relative grid grid-cols-5 gap-1 rounded-card p-1.5 shadow-float",
        className,
      )}
    >
      {statusCounts.map(({ status, label, count }) => {
        const isActive = status === value;
        return (
          <button
            key={status}
            type="button"
            aria-pressed={isActive}
            aria-label={`${label} ${count} 床`}
            disabled={count === 0 && !isActive}
            onClick={() => onChange(isActive ? "ALL" : status)}
            className={cn(
              "relative flex min-h-11 pressable items-center gap-2 rounded-xl px-2 py-2 focus-ring disabled:opacity-40 sm:gap-3 sm:px-3",
              !isActive && "hover:bg-fill",
            )}
          >
            {isActive && (
              <SelectionIndicator
                layoutId={indicatorLayoutId}
                className="rounded-xl bg-fill-strong"
              />
            )}
            <VerdictIcon verdict={status} className="relative size-7" />
            <span className="relative flex flex-col items-start">
              <span className="text-title tabular-nums">{count}</span>
              <span
                className={cn(
                  "text-caption font-medium whitespace-nowrap @xl:text-footnote",
                  isActive ? "text-ink" : "text-ink-secondary",
                )}
              >
                {label}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}
