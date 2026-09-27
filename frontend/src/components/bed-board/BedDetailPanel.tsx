"use client";

import { motion } from "motion/react";
import { type Ref, useId } from "react";

import { XIcon } from "@/components/ui/icons";
import { FADE_FAST, PANEL_MOTION, PANEL_TRANSITION } from "@/lib/motion";
import type { BedStatus } from "@/types/ward";

import { BedDetailContent } from "./BedDetailContent";
import { PatientPageLink } from "./PatientPageLink";

export const BED_DETAIL_PANEL_ID = "bed-detail";

type BedDetailPanelProps = {
  bed: BedStatus;
  businessDate: string;
  onClose: () => void;
  /** AnimatePresence（popLayout）量測位置與外部點擊判斷都需要 DOM 參照 */
  ref?: Ref<HTMLElement>;
};

/**
 * 桌機右側的病床詳情大卡：點選病床才浮現，與床位區並行、不遮擋，因此用液態玻璃而不加遮罩。
 * 進出動畫直接做在玻璃元素本身（祖先淡入會讓 backdrop-filter 暫時失效）；
 * 高度固定、內容區捲動（底緣以遮罩淡出），主要操作固定在底部，切換病床時大卡不會忽高忽低。
 */
export function BedDetailPanel({
  bed,
  businessDate,
  onClose,
  ref,
}: BedDetailPanelProps) {
  const headingId = useId();

  return (
    <motion.aside
      ref={ref}
      data-map-detail
      id={BED_DETAIL_PANEL_ID}
      aria-labelledby={headingId}
      initial={PANEL_MOTION.initial}
      animate={PANEL_MOTION.animate}
      exit={PANEL_MOTION.exit}
      transition={PANEL_TRANSITION}
      className="glass absolute top-5 right-5 bottom-5 z-30 flex w-detail origin-right flex-col overflow-hidden rounded-card shadow-float"
    >
      <motion.div
        key={bed.bedCode}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={FADE_FAST}
        className="flex min-h-0 flex-1 flex-col"
      >
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain mask-b-from-92% p-5 pb-6">
          <BedDetailContent
            bed={bed}
            businessDate={businessDate}
            headingId={headingId}
            headerAction={
              <button
                type="button"
                onClick={onClose}
                aria-label="關閉病床詳情"
                className="-mr-2 grid size-11 pressable place-items-center rounded-full text-ink-secondary focus-ring hover:bg-fill"
              >
                <XIcon weight="bold" aria-hidden="true" className="size-5" />
              </button>
            }
          />
        </div>
        <div className="shrink-0 px-5 pb-5">
          <PatientPageLink patientKey={bed.patient.patientKey} />
        </div>
      </motion.div>
    </motion.aside>
  );
}
