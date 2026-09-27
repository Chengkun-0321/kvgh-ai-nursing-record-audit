"use client";

import { useCallback, useState } from "react";

import { useOnMediaQueryMatch } from "@/hooks/useOnMediaQueryMatch";
import { DESKTOP_MEDIA_QUERY } from "@/lib/constants";
import { formatDate } from "@/lib/format";
import {
  countBedsByWorstVerdict,
  getDefaultSelectedBed,
  isBedDimmed,
  type VerdictFilterValue,
} from "@/lib/verdict";
import type { WardBedBoard } from "@/types/ward";

import { BedCard } from "./BedCard";
import { BedDetailPanel } from "./BedDetailPanel";
import { BedDetailSheet } from "./BedDetailSheet";
import { WardStatusBar } from "./WardStatusBar";

type BedBoardProps = {
  board: WardBedBoard;
};

/**
 * 病房病床總覽：床位區（依床號排列，對應實體位置）＋狀態列篩選＋病床詳情。
 * 桌機在右側顯示詳情面板；手機點選病床後以 bottom sheet 顯示。
 */
export function BedBoard({ board }: BedBoardProps) {
  const [activeFilter, setActiveFilter] = useState<VerdictFilterValue>("ALL");
  const [selectedBedCode, setSelectedBedCode] = useState(
    () => getDefaultSelectedBed(board.beds)?.bedCode,
  );
  const [hasUserSelected, setHasUserSelected] = useState(false);
  const [isSheetOpen, setIsSheetOpen] = useState(false);
  const closeSheet = useCallback(() => setIsSheetOpen(false), []);
  // 視窗放大到桌機寬度時 sheet 會被隱藏，須一併關閉以解除背景 inert
  useOnMediaQueryMatch(DESKTOP_MEDIA_QUERY, closeSheet);

  const selectedBed = board.beds.find((bed) => bed.bedCode === selectedBedCode);

  function handleSelectBed(bedCode: string) {
    setSelectedBedCode(bedCode);
    setHasUserSelected(true);
    if (!window.matchMedia(DESKTOP_MEDIA_QUERY).matches) {
      setIsSheetOpen(true);
    }
  }

  return (
    <div className="flex gap-6 px-4 py-6 lg:px-8 lg:py-8">
      <section
        aria-labelledby="ward-title"
        className="@container min-w-0 flex-1"
      >
        <header>
          <h1 id="ward-title" className="text-large-title">
            {board.wardCode} 病房
          </h1>
          <p className="mt-1 text-body text-ink-secondary">
            {board.wardName}｜共 {board.beds.length} 床｜稽核日期{" "}
            <span className="tabular-nums">
              {formatDate(board.businessDate)}
            </span>
          </p>
        </header>

        <div className="mt-6 flex flex-col rounded-panel ward-floor shadow-card">
          {/* DOM 順序＝桌機視覺順序（狀態列浮在床位區底部）；手機版以 order 移到上方 */}
          <ul className="grid grid-cols-2 gap-x-2 gap-y-3 p-3 lg:p-5 @xl:grid-cols-3 @xl:gap-x-4 @3xl:grid-cols-4 @5xl:grid-cols-5">
            {board.beds.map((bed) => (
              <li key={bed.bedCode}>
                <BedCard
                  bed={bed}
                  isSelected={bed.bedCode === selectedBedCode}
                  isDimmed={isBedDimmed(bed, activeFilter)}
                  onSelect={handleSelectBed}
                />
              </li>
            ))}
          </ul>
          <WardStatusBar
            bedCounts={countBedsByWorstVerdict(board.beds)}
            value={activeFilter}
            onChange={setActiveFilter}
            className="order-first m-3 lg:sticky lg:bottom-4 lg:z-20 lg:order-none lg:mx-5 lg:mt-0 lg:mb-5"
          />
        </div>
      </section>

      {selectedBed && (
        <div className="sticky top-[calc(var(--spacing-topbar)+1.5rem)] hidden max-h-[calc(100dvh-var(--spacing-topbar)-3rem)] w-detail shrink-0 self-start overflow-y-auto rounded-panel lg:block">
          <BedDetailPanel
            bed={selectedBed}
            businessDate={board.businessDate}
            shouldFade={hasUserSelected}
          />
        </div>
      )}

      <BedDetailSheet
        bed={selectedBed}
        businessDate={board.businessDate}
        isOpen={isSheetOpen}
        onClose={closeSheet}
      />
    </div>
  );
}
