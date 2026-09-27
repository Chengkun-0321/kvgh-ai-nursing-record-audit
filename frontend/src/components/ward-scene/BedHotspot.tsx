"use client";

import { motion } from "motion/react";
import { useRef } from "react";

import { VerdictIcon } from "@/components/VerdictIcon";
import { BED_DETAIL_PANEL_ID } from "@/components/bed-board/BedDetailPanel";
import { useMapKeyframe } from "@/hooks/useMapPlacement";
import { SPRING_DEFAULT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import {
  describeFindingCounts,
  getWorstVerdict,
  VERDICT_LABELS,
} from "@/lib/verdict";
import { VERDICT_STYLES } from "@/lib/verdictStyles";
import { getBedButtonId, type MapPoint } from "@/lib/wardMap";
import type { BedStatus } from "@/types/ward";

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
  const verdict = getWorstVerdict(bed.findings);
  useMapKeyframe(itemRef, {
    transform: `translate(${position.x}px, ${position.y}px)`,
  });

  return (
    <li ref={itemRef} className="bed-hotspot absolute top-0 left-0">
      <button
        id={getBedButtonId(bed.bedCode)}
        type="button"
        data-keep-detail
        data-bed-code={bed.bedCode}
        aria-pressed={isSelected}
        aria-controls={isSelected ? BED_DETAIL_PANEL_ID : undefined}
        aria-label={`${bed.bedCode}，${describeFindingCounts(bed.findings)}`}
        onClick={() => onToggle(bed.bedCode)}
        className="group absolute inset-0 rounded-[2rem] outline-none"
      >
        {isSelected && (
          <motion.span
            layoutId="bed-selection"
            transition={SPRING_DEFAULT}
            aria-hidden="true"
            className="absolute inset-0 rounded-[2rem] bg-surface/10 ring-2 ring-accent/70"
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
          {bed.bedCode}
          {verdict !== "PASS" && (
            <span
              className={cn("bed-label-verdict", VERDICT_STYLES[verdict].text)}
            >
              {VERDICT_LABELS[verdict]}
            </span>
          )}
        </span>
      </button>
    </li>
  );
}
