"use client";

import { motion } from "motion/react";

import { VerdictIcon } from "@/components/VerdictIcon";
import { getBedSpriteSrc } from "@/lib/bedSprites";
import { SPRING_DEFAULT } from "@/lib/motion";
import { cn } from "@/lib/utils";
import {
  describeFindingCounts,
  getWorstVerdict,
  VERDICT_LABELS,
} from "@/lib/verdict";
import { VERDICT_STYLES } from "@/lib/verdictStyles";
import { getBedButtonId } from "@/lib/wardMap";
import type { BedStatus } from "@/types/ward";

import { BED_DETAIL_PANEL_ID } from "./BedDetailPanel";
import { BedPhoto } from "./BedPhoto";

type BedCardProps = {
  bed: BedStatus;
  isSelected: boolean;
  isDimmed: boolean;
  onToggle: (bedCode: string) => void;
};

// 預留 200% 地圖縮放的圖片解析度，開卡不改變床位尺寸。
const BED_CARD_IMAGE_SIZES = "(min-width: 1024px) 380px, 75vw";

/**
 * 2D 病床卡（無 WebGL 時使用）：床號標籤＋病床圖片＋摘要。點擊開啟詳情，再點一次關閉。
 * 位置與大小以床位寬度（cqw）表示；窄床位只顯示最嚴重判定。
 */
export function BedCard({ bed, isSelected, isDimmed, onToggle }: BedCardProps) {
  const verdict = getWorstVerdict(bed.findings);
  const summary = describeFindingCounts(bed.findings);

  return (
    <button
      id={getBedButtonId(bed.bedCode)}
      type="button"
      data-keep-detail
      data-bed-code={bed.bedCode}
      aria-pressed={isSelected}
      aria-controls={isSelected ? BED_DETAIL_PANEL_ID : undefined}
      aria-label={`${bed.bedCode}，${summary}`}
      onClick={() => onToggle(bed.bedCode)}
      className={cn(
        "group absolute inset-0 rounded-[5cqw] focus-ring transition-opacity duration-300 ease-apple",
        isDimmed && "opacity-35",
      )}
    >
      {isSelected && (
        <motion.span
          layoutId="bed-selection"
          transition={SPRING_DEFAULT}
          aria-hidden="true"
          className="absolute inset-x-[14cqw] top-[15cqw] bottom-[11cqw] rounded-[8cqw] bg-surface/40 ring-2 ring-accent/30"
        />
      )}
      <span className="absolute top-[8cqw] left-[10cqw] w-[80cqw] transition-[translate,scale] duration-300 ease-apple group-hover:-translate-y-[0.5cqw] group-active:scale-97 group-active:duration-100">
        <BedPhoto
          src={getBedSpriteSrc(bed.patient, verdict)}
          sizes={BED_CARD_IMAGE_SIZES}
        />
      </span>
      <motion.span
        layout="position"
        transition={SPRING_DEFAULT}
        className={cn(
          "absolute inset-x-0 top-[2.5cqw] mx-auto flex w-fit items-center gap-1.5 rounded-full py-1 pr-3 pl-1.5 text-footnote font-semibold tabular-nums shadow-card transition-colors duration-200 ease-apple @min-[10rem]/bay:gap-2 @min-[10rem]/bay:py-1.5 @min-[10rem]/bay:pr-4 @min-[10rem]/bay:pl-2.5 @min-[10rem]/bay:text-headline",
          isSelected
            ? "bg-surface text-ink ring-2 ring-accent"
            : "bg-surface/90 text-ink",
        )}
      >
        <VerdictIcon
          verdict={verdict}
          className="size-4 @min-[10rem]/bay:size-5"
        />
        {bed.bedCode}
      </motion.span>
      <motion.span
        layout="position"
        transition={SPRING_DEFAULT}
        className={cn(
          "absolute inset-x-0 bottom-[1cqw] mx-auto w-fit max-w-[94cqw] rounded-full bg-surface px-2.5 py-1 text-center text-caption font-semibold text-balance shadow-card @min-[12rem]/bay:px-3 @min-[12rem]/bay:text-footnote",
          VERDICT_STYLES[verdict].text,
        )}
      >
        <span className="@min-[12rem]/bay:hidden">
          {VERDICT_LABELS[verdict]}
        </span>
        <span className="hidden @min-[12rem]/bay:inline">{summary}</span>
      </motion.span>
    </button>
  );
}
