"use client";

import { motion } from "motion/react";

import { VerdictIcon } from "@/components/VerdictIcon";
import { getBedSpriteSrc } from "@/lib/bedSprites";
import { SPRING_DEFAULT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { describeFindingCounts, getWorstVerdict } from "@/lib/verdict";
import { VERDICT_STYLES } from "@/lib/verdictStyles";
import type { BedStatus } from "@/types/ward";

import { BED_DETAIL_PANEL_ID } from "./BedDetailPanel";
import { BedPhoto } from "./BedPhoto";

type BedCardProps = {
  bed: BedStatus;
  isSelected: boolean;
  isDimmed: boolean;
  onSelect: (bedCode: string) => void;
};

// 床位區以 container query 排版，每床顯示寬度約 170–260px
const BED_CARD_IMAGE_SIZES =
  "(min-width: 1024px) 260px, (min-width: 640px) 33vw, 50vw";

/** 單一病床：床號標籤＋病床圖片＋摘要；點擊選取並於詳情面板顯示。 */
export function BedCard({ bed, isSelected, isDimmed, onSelect }: BedCardProps) {
  const verdict = getWorstVerdict(bed.findings);
  const summary = describeFindingCounts(bed.findings);

  return (
    <button
      type="button"
      aria-pressed={isSelected}
      aria-controls={BED_DETAIL_PANEL_ID}
      aria-label={`${bed.bedCode}，${summary}`}
      onClick={() => onSelect(bed.bedCode)}
      className={cn(
        "group relative flex w-full flex-col items-center rounded-card pt-3 focus-ring transition-[opacity,filter] duration-300 ease-apple",
        isDimmed && "opacity-35 saturate-50",
      )}
    >
      {isSelected && (
        <motion.span
          layoutId="bed-selection"
          transition={SPRING_DEFAULT}
          aria-hidden="true"
          className="absolute inset-0 rounded-card bg-surface/60 shadow-card ring-1 ring-surface"
        />
      )}
      <span
        className={cn(
          "relative z-10 -mb-3 inline-flex items-center gap-2 rounded-full py-1.5 pr-4 pl-2.5 text-headline tabular-nums shadow-card transition-colors duration-200 ease-apple",
          isSelected ? "bg-accent text-accent-contrast" : "bg-surface text-ink",
        )}
      >
        <VerdictIcon verdict={verdict} className="size-5" />
        {bed.bedCode}
      </span>
      <span className="relative w-full transition-[translate,scale] duration-200 ease-apple group-hover:-translate-y-1 group-active:scale-97 group-active:duration-100">
        <BedPhoto
          src={getBedSpriteSrc(bed.patient, verdict)}
          sizes={BED_CARD_IMAGE_SIZES}
        />
      </span>
      <span
        className={cn(
          "relative -mt-12 mb-3 rounded-full bg-surface/90 px-2.5 py-1 text-caption font-semibold whitespace-nowrap shadow-card sm:px-3 sm:text-footnote",
          VERDICT_STYLES[verdict].text,
        )}
      >
        {summary}
      </span>
    </button>
  );
}
