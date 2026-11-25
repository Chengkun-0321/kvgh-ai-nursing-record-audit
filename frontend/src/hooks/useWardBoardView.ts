import { useState, useSyncExternalStore } from "react";

import {
  DEFAULT_WARD_BOARD_VIEW,
  readWardBoardView,
  type WardBoardView,
  writeWardBoardView,
} from "@/lib/wardBoardView";

function subscribe(onChange: () => void): () => void {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

/** 伺服器與水合前預設清單，水合後還原偏好；儲存失敗仍保留本頁選擇。 */
export function useWardBoardView() {
  const storedView = useSyncExternalStore(
    subscribe,
    readWardBoardView,
    () => DEFAULT_WARD_BOARD_VIEW,
  );
  const [selection, setSelection] = useState<WardBoardView>();
  function setView(view: WardBoardView) {
    setSelection(view);
    writeWardBoardView(view);
  }
  return { view: selection ?? storedView, setView };
}
