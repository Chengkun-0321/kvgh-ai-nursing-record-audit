"use client";

import { SelectionIndicator } from "@/components/ui/SelectionIndicator";
import { cn } from "@/lib/utils";
import type { WardViewId } from "@/lib/wardKit";

type ViewToggleProps = {
  value: WardViewId;
  onChange: (viewId: WardViewId) => void;
};

const VIEW_OPTIONS: readonly { value: WardViewId; label: string }[] = [
  { value: "straight", label: "正視" },
  { value: "tilted", label: "斜視" },
];

/** 病房視角切換（正視／斜視）；選取底色以 spring 滑動，按鈕以 aria-pressed 表示目前視角。 */
export function ViewToggle({ value, onChange }: ViewToggleProps) {
  return (
    <div
      role="group"
      aria-label="病房視角"
      className="flex gap-0.5 rounded-xl bg-fill p-0.5"
    >
      {VIEW_OPTIONS.map((option) => {
        const isSelected = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            aria-pressed={isSelected}
            onClick={() => onChange(option.value)}
            className={cn(
              "relative min-h-11 min-w-11 pressable rounded-lg px-2.5 text-footnote focus-ring",
              isSelected ? "font-semibold text-ink" : "text-ink-secondary",
            )}
          >
            {isSelected && (
              <SelectionIndicator
                layoutId="map-view-indicator"
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
