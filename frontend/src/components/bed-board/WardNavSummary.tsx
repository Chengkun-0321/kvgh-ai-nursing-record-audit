import { formatDate } from "@/lib/format";
import type { WardBedBoard } from "@/lib/api/wards";

type WardNavSummaryProps = {
  board: WardBedBoard;
};

/**
 * 頂部左側膠囊內的病房資訊（病房名、床數、稽核日期），只在首頁顯示。
 * 桌機導覽與手機頂列各放一份，另一份隨外框隱藏；頁面標題（h1）仍在首頁內，供病床清單的 `aria-labelledby` 使用。
 */
export function WardNavSummary({ board }: WardNavSummaryProps) {
  return (
    <div
      data-nav-context
      className="flex min-w-0 items-center gap-3 pr-3 xl:pr-0"
    >
      <span aria-hidden="true" className="h-7 w-px shrink-0 bg-separator" />
      <p className="flex min-w-0 flex-col leading-tight">
        <span className="truncate text-headline">{board.display_name}</span>
        <span className="truncate text-caption text-ink-secondary tabular-nums">
          {board.bed_count} 床・稽核日期 {formatDate(board.business_date)}
        </span>
      </p>
    </div>
  );
}
