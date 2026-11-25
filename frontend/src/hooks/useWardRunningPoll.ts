import { useRouter } from "next/navigation";
import { useEffect } from "react";

import type { WardBedBoard } from "@/lib/api/wards";
import { AUDIT_RUNNING_POLL_MS } from "@/lib/constants";

/** 只有後端回報格子稽核中時才刷新首頁；全部結束、換病房日期或卸載時清理計時器。 */
export function useWardRunningPoll(board: WardBedBoard): void {
  const router = useRouter();
  const isRunning = board.beds.some((bed) =>
    bed.rule_cells.some((cell) => cell.state === "RUNNING"),
  );
  useEffect(() => {
    if (!isRunning) return;
    const timer = setInterval(() => router.refresh(), AUDIT_RUNNING_POLL_MS);
    return () => clearInterval(timer);
  }, [isRunning, router, board.ward_code, board.business_date]);
}
