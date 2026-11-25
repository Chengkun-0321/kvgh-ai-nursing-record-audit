export type WardBoardView = "list" | "3d";
export const DEFAULT_WARD_BOARD_VIEW: WardBoardView = "list";
export const WARD_BOARD_VIEW_STORAGE_KEY = "ward-board-view";

/** 無瀏覽器、儲存遭封鎖或值無效時，首頁一律以清單開啟。 */
export function readWardBoardView(): WardBoardView {
  try {
    return window.localStorage.getItem(WARD_BOARD_VIEW_STORAGE_KEY) === "3d"
      ? "3d"
      : DEFAULT_WARD_BOARD_VIEW;
  } catch {
    return DEFAULT_WARD_BOARD_VIEW;
  }
}

/** 儲存檢視偏好；儲存失敗時仍允許本頁切換，不影響病床操作。 */
export function writeWardBoardView(view: WardBoardView): void {
  try {
    window.localStorage.setItem(WARD_BOARD_VIEW_STORAGE_KEY, view);
  } catch {
    // 隱私模式可能禁止存取；本頁選擇由 hook 的狀態保留。
  }
}
