import type { WardBedBoard } from "@/lib/api/wards";

export const WARD_TITLE_ID = "ward-title";

/**
 * 首頁的頁面標題，只供螢幕閱讀器與病床清單的 `aria-labelledby` 使用；
 * 畫面上的病房資訊改放在頂部左側膠囊（`WardNavSummary`），不再疊在病房上擋住床位。
 */
export function WardTitle({ board }: { board: WardBedBoard }) {
  return (
    <h1 id={WARD_TITLE_ID} className="sr-only">
      {board.display_name}
    </h1>
  );
}
