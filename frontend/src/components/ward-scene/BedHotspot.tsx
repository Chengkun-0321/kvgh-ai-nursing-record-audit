"use client";

import { useRef } from "react";

import { SelectionIndicator } from "@/components/ui/SelectionIndicator";
import { VerdictIcon } from "@/components/VerdictIcon";
import { BED_DETAIL_PANEL_ID } from "@/components/bed-board/BedDetailPanel";
import { useMapKeyframe } from "@/hooks/useMapKeyframe";
import { cn } from "@/lib/utils";
import { VERDICT_STYLES } from "@/lib/verdictStyles";
import { getBedButtonId, type MapPoint } from "@/lib/wardMap";
import type { BedStatus } from "@/lib/api/wards";

type BedHotspotProps = {
  bed: BedStatus;
  position: MapPoint;
  isSelected: boolean;
  isDimmed: boolean;
  onToggle: (bedCode: string) => void;
};

/**
 * 病床的可點範圍（疊在 3D 去背圖上，本身透明）與床號標籤。
 * 標籤以 --map-scale 反向縮放，地圖縮放時字級不變；判定以「顏色＋圖示＋文字」呈現。
 */
export function BedHotspot({
  bed,
  position,
  isSelected,
  isDimmed,
  onToggle,
}: BedHotspotProps) {
  const itemRef = useRef<HTMLLIElement>(null);
  const verdict = bed.status;
  useMapKeyframe(itemRef, {
    transform: `translate(${position.x}px, ${position.y}px)`,
  });

  return (
    <li ref={itemRef} className="bed-hotspot absolute top-0 left-0">
      <button
        id={getBedButtonId(bed.bed_code)}
        type="button"
        data-keep-detail
        data-bed-code={bed.bed_code}
        aria-pressed={isSelected}
        aria-controls={isSelected ? BED_DETAIL_PANEL_ID : undefined}
        aria-label={`${bed.bed_code}，${bed.summary_text}`}
        onClick={() => onToggle(bed.bed_code)}
        className="group absolute inset-0 rounded-[2rem] outline-none"
      >
        {isSelected && (
          <SelectionIndicator
            layoutId="bed-selection"
            className="rounded-[2rem] bg-surface/10 ring-2 ring-accent/70"
          />
        )}
        <span
          className={cn(
            "bed-label flex items-center gap-1.5 rounded-full py-1 pr-3 pl-1.5 text-footnote font-semibold whitespace-nowrap tabular-nums shadow-card transition-[opacity,box-shadow] duration-300 ease-apple group-hover:shadow-float group-focus-visible:outline-2 group-focus-visible:outline-offset-2 group-focus-visible:outline-accent",
            isSelected
              ? "bg-surface text-ink ring-2 ring-accent"
              : "bg-surface/90 text-ink",
            isDimmed && "opacity-35",
          )}
        >
          <VerdictIcon verdict={verdict} className="size-4" />
          {bed.bed_code}
          {bed.is_pending && (
            <span
              className={cn("bed-label-verdict", VERDICT_STYLES[verdict].text)}
            >
              {bed.status_label}
            </span>
          )}
        </span>
      </button>
    </li>
  );
}
