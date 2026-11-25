"use client";

import { AnimatePresence } from "motion/react";
import { useRef, useState } from "react";

import { type DismissReason, useDismissable } from "@/hooks/useDismissable";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useWardBoardView } from "@/hooks/useWardBoardView";
import { useWardRunningPoll } from "@/hooks/useWardRunningPoll";
import { DESKTOP_MEDIA_QUERY } from "@/lib/constants";
import type { BedFilterValue } from "@/lib/verdict";
import { getBedButtonId } from "@/lib/wardMap";
import type { WardBedBoard } from "@/lib/api/wards";

import { BedDetailPanel } from "./BedDetailPanel";
import { BedDetailSheet } from "./BedDetailSheet";
import { WardPatientList } from "./WardPatientList";
import { WardRoomView } from "./WardRoomView";
import { WardTitle } from "./WardTitle";
import { WardStatusBar } from "./WardStatusBar";
import { WardViewTogglePortal } from "./WardViewToggle";

type BedBoardProps = {
  board: WardBedBoard;
};

// 點到病床或狀態列不算「點外部」：切換病床、篩選時大卡保持開啟
const KEEP_DETAIL_SELECTOR = "[data-keep-detail]";

/**
 * 病房總覽預設清單，可切換 3D 病房；兩種檢視共用選取、詳情與執行中輪詢。
 * 狀態列（依判定篩選）只在 3D 病房顯示；清單本身已逐格列出結果，不篩選。
 * 檢視切換以 portal 放進頂部導覽的插槽（桌機與手機各一個）。
 */
export function BedBoard({ board }: BedBoardProps) {
  const isDesktop = useMediaQuery(DESKTOP_MEDIA_QUERY);
  const { view, setView } = useWardBoardView();
  useWardRunningPoll(board);
  const [activeFilter, setActiveFilter] = useState<BedFilterValue>("ALL");
  const [selectedBedCode, setSelectedBedCode] = useState<string>();
  const panelRef = useRef<HTMLElement>(null);
  const selectedBed = board.beds.find(
    (bed) => bed.bed_code === selectedBedCode,
  );
  const hasDesktopDetail = isDesktop && selectedBed !== undefined;

  function closeDetail(reason: DismissReason | "button") {
    // 以按鈕或 Esc 關閉時把焦點送回原病床，鍵盤使用者不會失去位置
    if (reason !== "outside" && selectedBedCode) {
      document
        .getElementById(getBedButtonId(selectedBedCode))
        ?.focus({ preventScroll: true });
    }
    setSelectedBedCode(undefined);
  }
  useDismissable({
    isActive: hasDesktopDetail,
    containerRef: panelRef,
    keepSelector: KEEP_DETAIL_SELECTOR,
    onDismiss: closeDetail,
  });

  function handleToggleBed(bedCode: string) {
    setSelectedBedCode((current) =>
      current === bedCode ? undefined : bedCode,
    );
  }

  return (
    <div
      className="ward-stage relative isolate"
      data-detail-open={hasDesktopDetail}
    >
      {view === "3d" && (
        <WardRoomView
          board={board}
          selectedBedCode={selectedBedCode}
          activeFilter={activeFilter}
          onToggle={handleToggleBed}
          onBackgroundClick={() => closeDetail("outside")}
        />
      )}
      {/* 固定介面放在安全區內：病房鋪滿整個視窗，頂部導覽（手機為頂列）疊在場景上 */}
      <div className="ward-safe">
        <WardTitle board={board} />
        {view === "list" && (
          <WardPatientList
            board={board}
            selectedBedCode={selectedBedCode}
            onToggle={handleToggleBed}
          />
        )}
        {view === "3d" && (
          <div
            data-keep-detail
            className="ward-status pointer-events-auto absolute bottom-4 left-4 z-20"
          >
            <WardStatusBar
              statusCounts={board.status_counts}
              value={activeFilter}
              onChange={setActiveFilter}
            />
          </div>
        )}
        <AnimatePresence>
          {hasDesktopDetail && (
            <BedDetailPanel
              key="bed-detail"
              ref={panelRef}
              bed={selectedBed}
              onClose={() => closeDetail("button")}
            />
          )}
        </AnimatePresence>
      </div>
      <WardViewTogglePortal
        isDesktop={isDesktop}
        value={view}
        onChange={setView}
      />
      <BedDetailSheet
        bed={selectedBed}
        isOpen={!isDesktop && selectedBed !== undefined}
        onClose={() => setSelectedBedCode(undefined)}
      />
    </div>
  );
}
