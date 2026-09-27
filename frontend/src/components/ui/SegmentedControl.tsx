"use client";

import { useId } from "react";

import { cn } from "@/lib/utils";

import { SelectionIndicator } from "./SelectionIndicator";

export type SegmentOption<T extends string> = {
  value: T;
  label: string;
  disabledHint?: string;
};

type SegmentedControlProps<T extends string> = {
  options: readonly SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  ariaLabel: string;
  panelId: string;
};

/**
 * Apple 風格分段控制器（分頁）；選取指示器以 spring 在項目間滑動。
 * 有 `disabledHint` 的項目為停用，保留位置但不可切換。
 */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
  panelId,
}: SegmentedControlProps<T>) {
  const indicatorLayoutId = useId();

  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className="grid auto-cols-fr grid-flow-col gap-0.5 rounded-xl bg-fill p-0.5"
    >
      {options.map((option) => {
        const isSelected = option.value === value;
        const isDisabled = option.disabledHint !== undefined;
        return (
          <button
            key={option.value}
            type="button"
            role="tab"
            aria-selected={isSelected}
            aria-controls={isSelected ? panelId : undefined}
            aria-disabled={isDisabled || undefined}
            title={option.disabledHint}
            onClick={() => !isDisabled && onChange(option.value)}
            className={cn(
              "relative min-h-11 rounded-lg px-1.5 text-footnote font-medium focus-ring",
              isDisabled
                ? "cursor-not-allowed text-ink/35"
                : "pressable text-ink",
            )}
          >
            {isSelected && (
              <SelectionIndicator
                layoutId={indicatorLayoutId}
                className="rounded-lg bg-surface shadow-card"
              />
            )}
            <span className="relative">{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}
