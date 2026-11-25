import { WardNavSummary } from "@/components/bed-board/WardNavSummary";
import { getDefaultWardCode, getWardBedBoard } from "@/lib/api/wards";

async function loadBoard() {
  return getWardBedBoard(await getDefaultWardCode());
}

/**
 * 首頁（病房總覽）放在頂部左側膠囊的病房資訊。資料與首頁共用同一次請求（`cache`），不重複呼叫後端；
 * 取得失敗時不顯示，由首頁本身顯示錯誤。
 */
export default async function NavContextHome() {
  const board = await loadBoard().catch(() => null);
  return board ? <WardNavSummary board={board} /> : null;
}
