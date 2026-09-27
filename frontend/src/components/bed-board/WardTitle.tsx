import { formatDate } from "@/lib/format";
import type { WardBedBoard } from "@/types/ward";

export const WARD_TITLE_ID = "ward-title";

/** 病房標題固定在場景外，縮放時保持字級及位置。 */
export function WardTitle({ board }: { board: WardBedBoard }) {
  return (
    <header className="ward-title pointer-events-none absolute top-0 left-0 z-10 px-6 pt-5 pb-6 text-on-chrome">
      <h1 id={WARD_TITLE_ID} className="text-large-title">
        {board.wardCode} 病房
      </h1>
      <p className="mt-1 text-body text-on-chrome-secondary">
        {board.wardName}{" "}
        <span aria-hidden="true" className="mx-2">
          ｜
        </span>{" "}
        共 {board.beds.length} 床
      </p>
      <p className="mt-1 text-caption text-on-chrome-secondary">
        稽核日期 {formatDate(board.businessDate)}
      </p>
    </header>
  );
}
