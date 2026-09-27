"use client";

import { motion } from "motion/react";
import { useId } from "react";

import { FADE_FAST } from "@/lib/motion";
import type { BedStatus } from "@/types/ward";

import { BedDetailContent } from "./BedDetailContent";

export const BED_DETAIL_PANEL_ID = "bed-detail";

type BedDetailPanelProps = {
  bed: BedStatus;
  businessDate: string;
  /** 使用者切換過病床才淡入；首屏不做進場動畫，避免 JS 載入前內容不可見 */
  shouldFade: boolean;
};

/** 桌機右側的病床詳情面板：與床位區並行、不遮擋，因此用半透明材質而不加遮罩。 */
export function BedDetailPanel({
  bed,
  businessDate,
  shouldFade,
}: BedDetailPanelProps) {
  const headingId = useId();

  return (
    <aside
      id={BED_DETAIL_PANEL_ID}
      aria-labelledby={headingId}
      className="rounded-panel glass p-5 shadow-float"
    >
      <motion.div
        key={bed.bedCode}
        initial={shouldFade ? { opacity: 0 } : false}
        animate={{ opacity: 1 }}
        transition={FADE_FAST}
      >
        <BedDetailContent
          bed={bed}
          businessDate={businessDate}
          headingId={headingId}
        />
      </motion.div>
    </aside>
  );
}
