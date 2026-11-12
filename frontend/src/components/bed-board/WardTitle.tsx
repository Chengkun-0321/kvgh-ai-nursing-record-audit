import { formatDate } from "@/lib/format";
import type { WardBedBoard } from "@/lib/api/wards";

export const WARD_TITLE_ID = "ward-title";

/** 病房標題：左上角的淺色玻璃卡片，固定在場景外，縮放時保持字級及位置。 */
export function WardTitle({ board }: { board: WardBedBoard }) {
  return (
    <header className="ward-title glass pointer-events-none absolute top-4 left-4 z-10 max-w-[calc(100%-2rem)] rounded-card px-5 py-3 shadow-float">
      <h1 id={WARD_TITLE_ID} className="text-title">
        {board.display_name}
      </h1>
      <p className="mt-1 text-footnote text-ink-secondary">
        共 {board.bed_count} 床
        <span aria-hidden="true" className="mx-1.5">
          ｜
        </span>
        稽核日期{" "}
        <span className="tabular-nums">{formatDate(board.business_date)}</span>
      </p>
    </header>
  );
}
