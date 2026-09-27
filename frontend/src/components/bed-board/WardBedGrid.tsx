import { isBedDimmed, type VerdictFilterValue } from "@/lib/verdict";
import type { WardBedBoard } from "@/types/ward";

import { BedCard } from "./BedCard";
import { WARD_TITLE_ID } from "./WardTitle";

type WardBedGridProps = {
  board: WardBedBoard;
  selectedBedCode?: string;
  activeFilter: VerdictFilterValue;
  onToggle: (bedCode: string) => void;
};

/** 無法使用 WebGL（沒有 GPU、場景載入失敗）時的 2D 病床清單，功能與 3D 地圖相同。 */
export function WardBedGrid({
  board,
  selectedBedCode,
  activeFilter,
  onToggle,
}: WardBedGridProps) {
  return (
    <div className="pointer-events-auto absolute inset-0 overflow-y-auto px-6 pt-32 pb-28">
      {board.beds.length === 0 ? (
        <p className="mx-auto w-fit rounded-card bg-surface px-8 py-6 text-headline">
          目前沒有床位資料
        </p>
      ) : (
        <ul
          className="grid grid-cols-[repeat(auto-fill,minmax(11rem,1fr))] gap-6"
          aria-labelledby={WARD_TITLE_ID}
        >
          {board.beds.map((bed) => (
            <li
              key={bed.bedCode}
              className="@container/bay relative aspect-20/23"
            >
              <BedCard
                bed={bed}
                isSelected={bed.bedCode === selectedBedCode}
                isDimmed={isBedDimmed(bed, activeFilter)}
                onToggle={onToggle}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
