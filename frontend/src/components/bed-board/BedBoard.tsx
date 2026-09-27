"use client";

import { AnimatePresence } from "motion/react";
import { useCallback, useRef, useState } from "react";

import { WardMap } from "@/components/ward-scene/WardMap";
import { type DismissReason, useDismissable } from "@/hooks/useDismissable";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useWardSceneMode } from "@/hooks/useWebGLSupport";
import { DESKTOP_MEDIA_QUERY } from "@/lib/constants";
import {
  countBedsByWorstVerdict,
  type VerdictFilterValue,
} from "@/lib/verdict";
import { getBedButtonId } from "@/lib/wardMap";
import type { WardBedBoard } from "@/types/ward";

import { BedDetailPanel } from "./BedDetailPanel";
import { BedDetailSheet } from "./BedDetailSheet";
import { WardBedGrid } from "./WardBedGrid";
import { WardTitle } from "./WardTitle";
import { WardStatusBar } from "./WardStatusBar";

type BedBoardProps = {
  board: WardBedBoard;
};

// 點到病床或狀態列不算「點外部」：切換病床、篩選時大卡保持開啟
const KEEP_DETAIL_SELECTOR = "[data-keep-detail]";

/** 病房總覽：3D 病房地圖（不支援 WebGL 時改用 2D 清單）＋狀態列篩選＋詳情卡。 */
export function BedBoard({ board }: BedBoardProps) {
  const isDesktop = useMediaQuery(DESKTOP_MEDIA_QUERY);
  const { mode: sceneMode, reportSceneError } = useWardSceneMode();
  const [activeFilter, setActiveFilter] = useState<VerdictFilterValue>("ALL");
  const [selectedBedCode, setSelectedBedCode] = useState<string>();
  const panelRef = useRef<HTMLElement>(null);
  const selectedBed = board.beds.find((bed) => bed.bedCode === selectedBedCode);

  const closeDetail = useCallback(
    (reason: DismissReason | "button") => {
      // 以按鈕或 Esc 關閉時把焦點送回原病床，鍵盤使用者不會失去位置
      if (reason !== "outside" && selectedBedCode) {
        document
          .getElementById(getBedButtonId(selectedBedCode))
          ?.focus({ preventScroll: true });
      }
      setSelectedBedCode(undefined);
    },
    [selectedBedCode],
  );
  useDismissable({
    isActive: isDesktop && selectedBed !== undefined,
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
      data-detail-open={isDesktop && selectedBed ? "true" : "false"}
    >
      {sceneMode === "2d" ? (
        <div className="ward-safe">
          <WardBedGrid
            board={board}
            selectedBedCode={selectedBedCode}
            activeFilter={activeFilter}
            onToggle={handleToggleBed}
          />
        </div>
      ) : (
        <WardMap
          board={board}
          selectedBedCode={selectedBedCode}
          activeFilter={activeFilter}
          isSceneEnabled={sceneMode === "3d"}
          onToggle={handleToggleBed}
          onBackgroundClick={() => closeDetail("outside")}
          onSceneError={reportSceneError}
        />
      )}
      {/* 固定介面放在安全區內：病房鋪滿整個視窗，頂列與側欄疊在場景上 */}
      <div className="ward-safe">
        <WardTitle board={board} />
        <div
          data-keep-detail
          className="ward-status pointer-events-auto absolute bottom-5 left-5 z-20"
        >
          <WardStatusBar
            bedCounts={countBedsByWorstVerdict(board.beds)}
            value={activeFilter}
            onChange={setActiveFilter}
          />
        </div>
        <AnimatePresence>
          {isDesktop && selectedBed && (
            <BedDetailPanel
              key="bed-detail"
              ref={panelRef}
              bed={selectedBed}
              businessDate={board.businessDate}
              onClose={() => closeDetail("button")}
            />
          )}
        </AnimatePresence>
      </div>
      <BedDetailSheet
        bed={selectedBed}
        businessDate={board.businessDate}
        isOpen={!isDesktop && selectedBed !== undefined}
        onClose={() => setSelectedBedCode(undefined)}
      />
    </div>
  );
}
