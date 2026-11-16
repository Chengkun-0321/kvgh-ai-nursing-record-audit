"use client";

import { motion, type PanInfo, useDragControls } from "motion/react";
import { useEffect, useId, useRef } from "react";

import type { AuditRuleView } from "@/hooks/useAuditRuns";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import {
  AUDIT_RESULT_DESKTOP_MOTION,
  AUDIT_RESULT_SHEET_MOTION,
  SHEET_DRAG_ELASTIC,
  shouldDismissSheet,
} from "@/lib/motion";

import { AuditResultBody } from "./AuditResultBody";

const DESKTOP_QUERY = "(min-width: 64rem)";

type AuditResultDialogProps = {
  /** 目前要顯示結果的規則；undefined 時關閉 */
  rule: AuditRuleView | undefined;
  onClose: () => void;
};

/**
 * 稽核結果視窗：原生 `<dialog>` 的 `showModal()` 提供 Esc 關閉、背景 inert 與焦點還原。
 * 桌機為置中面板，手機為底部抽屜（可拖曳把手關閉，沿用 BedDetailSheet 的做法）。
 */
export function AuditResultDialog({ rule, onClose }: AuditResultDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const dragControls = useDragControls();
  const titleId = useId();
  const isDesktop = useMediaQuery(DESKTOP_QUERY);
  const entrance = isDesktop
    ? AUDIT_RESULT_DESKTOP_MOTION
    : AUDIT_RESULT_SHEET_MOTION;

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) {
      return;
    }
    if (rule && !dialog.open) {
      dialog.showModal();
    }
    if (!rule && dialog.open) {
      dialog.close();
    }
  }, [rule]);

  function handleDragEnd(
    _event: PointerEvent | MouseEvent | TouchEvent,
    info: PanInfo,
  ) {
    const heightPx = panelRef.current?.offsetHeight ?? window.innerHeight;
    if (shouldDismissSheet(info.offset.y, info.velocity.y, heightPx)) {
      onClose();
    }
  }

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      onClose={onClose}
      onClick={(event) => {
        // 點到背景（dialog 本身）即關閉
        if (event.target === dialogRef.current) {
          onClose();
        }
      }}
      className="fixed inset-x-0 top-auto bottom-0 m-0 max-h-[90dvh] w-full max-w-none overflow-visible border-0 bg-transparent p-0 backdrop:bg-scrim lg:inset-0 lg:m-auto lg:h-fit lg:w-[min(42rem,calc(100vw-4rem))]"
    >
      {rule && (
        <motion.div
          key={rule.rule_code}
          ref={panelRef}
          {...entrance}
          drag={isDesktop ? false : "y"}
          dragListener={false}
          dragControls={dragControls}
          dragConstraints={{ top: 0, bottom: 0 }}
          dragElastic={SHEET_DRAG_ELASTIC}
          onDragEnd={handleDragEnd}
          className="flex max-h-[90dvh] flex-col rounded-t-panel bg-surface shadow-float lg:max-h-[85dvh] lg:rounded-panel"
        >
          <div
            onPointerDown={(event) => dragControls.start(event)}
            className="flex shrink-0 cursor-grab touch-none justify-center pt-2.5 pb-1 lg:hidden"
          >
            <span
              aria-hidden="true"
              className="h-1.5 w-10 rounded-full bg-fill-strong"
            />
          </div>
          <AuditResultBody rule={rule} titleId={titleId} onClose={onClose} />
        </motion.div>
      )}
    </dialog>
  );
}
