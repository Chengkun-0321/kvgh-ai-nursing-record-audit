"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/**
 * 進入病房總覽時向伺服器重新取得目前路由，不渲染任何內容。
 *
 * 原因：瀏覽器返回（back/forward）會直接使用 Client Cache 中的舊 RSC payload，病患頁執行稽核後
 * 首頁仍顯示舊結果；站內導覽雖會重新取得頁面，但共用的 layout（頂部待處理床數）不會重新取得。
 * `router.refresh()` 會重新取得目前路由（含 layout）並保留頁面的 client state（例如選取的病床）。
 */
export function BoardRefresher() {
  const router = useRouter();

  useEffect(() => {
    router.refresh();
  }, [router]);

  return null;
}
