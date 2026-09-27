"use client";

import {
  AnimatePresence,
  motion,
  type PanInfo,
  useDragControls,
} from "motion/react";
import { useEffect, useId, useRef } from "react";

import { XIcon } from "@/components/ui/icons";
import {
  FADE_SCRIM,
  SHEET_DRAG_ELASTIC,
  SHEET_TRANSITION,
  shouldDismissSheet,
} from "@/lib/motion";
import type { BedStatus } from "@/types/ward";

import { BED_DETAIL_PANEL_ID } from "./BedDetailPanel";
import { BedDetailContent } from "./BedDetailContent";
import { PatientPageLink } from "./PatientPageLink";

type BedDetailSheetProps = {
  bed: BedStatus | undefined;
  businessDate: string;
  isOpen: boolean;
  onClose: () => void;
};

/**
 * 手機／平板的病床詳情 bottom sheet。
 * 以原生 `<dialog>` 取得 Esc 關閉、背景 inert 與焦點還原；由下進、往下退，
 * 可拖曳把手關閉（依放手速度投影判斷，速度交給退場 spring 延續）。
 */
export function BedDetailSheet({
  bed,
  businessDate,
  isOpen,
  onClose,
}: BedDetailSheetProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const sheetRef = useRef<HTMLDivElement>(null);
  const dragControls = useDragControls();
  const headingId = useId();
  const isVisible = isOpen && bed !== undefined;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (isVisible && dialog && !dialog.open) {
      dialog.showModal();
    }
  }, [isVisible]);

  function handleDragEnd(
    _event: PointerEvent | MouseEvent | TouchEvent,
    info: PanInfo,
  ) {
    const sheetHeightPx = sheetRef.current?.offsetHeight ?? window.innerHeight;
    if (shouldDismissSheet(info.offset.y, info.velocity.y, sheetHeightPx)) {
      onClose();
    }
  }

  return (
    <dialog
      ref={dialogRef}
      id={isVisible ? BED_DETAIL_PANEL_ID : undefined}
      aria-labelledby={headingId}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      className="fixed inset-0 m-0 size-full max-h-none max-w-none overflow-hidden border-0 bg-transparent p-0 backdrop:bg-transparent lg:hidden"
    >
      <AnimatePresence onExitComplete={() => dialogRef.current?.close()}>
        {isVisible && (
          <motion.div
            key="scrim"
            aria-hidden="true"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={FADE_SCRIM}
            className="absolute inset-0 bg-scrim"
          />
        )}
        {isVisible && (
          <motion.div
            key="sheet"
            ref={sheetRef}
            initial={{ y: "100%", opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: "100%", opacity: 0 }}
            transition={SHEET_TRANSITION}
            drag="y"
            dragListener={false}
            dragControls={dragControls}
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={SHEET_DRAG_ELASTIC}
            onDragEnd={handleDragEnd}
            className="absolute inset-x-0 bottom-0 flex max-h-[90dvh] flex-col rounded-t-panel bg-surface shadow-float"
          >
            <div
              onPointerDown={(event) => dragControls.start(event)}
              className="relative flex shrink-0 cursor-grab touch-none justify-end px-3 pt-3 active:cursor-grabbing"
            >
              <span
                aria-hidden="true"
                className="absolute top-2 left-1/2 h-1.5 w-10 -translate-x-1/2 rounded-full bg-fill-strong"
              />
              <button
                type="button"
                onClick={onClose}
                aria-label="關閉病床詳情"
                className="grid size-11 pressable place-items-center rounded-full text-ink-secondary focus-ring hover:bg-fill"
              >
                <XIcon weight="bold" aria-hidden="true" className="size-5" />
              </button>
            </div>
            <div className="overflow-y-auto overscroll-contain px-5 pb-[calc(env(safe-area-inset-bottom)+1.5rem)]">
              <BedDetailContent
                bed={bed}
                businessDate={businessDate}
                headingId={headingId}
              />
              <PatientPageLink
                patientKey={bed.patient.patientKey}
                className="mt-5"
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </dialog>
  );
}
