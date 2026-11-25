import type { RuleCellState } from "@/lib/api/wards";

import { RuleCellBadge } from "./RuleCellBadge";

// 圖例只說明視覺對照；病患格子的文字與數量一律來自 API。
const LEGEND: { state: RuleCellState; label: string }[] = [
  { state: "PASS", label: "紀錄完整" },
  { state: "WARNING", label: "需確認" },
  { state: "NEEDS_REVIEW", label: "無法判定" },
  { state: "ERROR", label: "缺漏" },
  { state: "RUNNING", label: "稽核中" },
  { state: "FAILED", label: "執行失敗" },
  { state: "NOT_APPLICABLE", label: "當日無此事件" },
  { state: "DATA_UNAVAILABLE", label: "院方尚未提供資料" },
  { state: "DAY_NOT_ENDED", label: "當日尚未結束" },
  { state: "NOT_AUDITED", label: "尚未稽核" },
];

/** 狀態圖例與發現數說明，維持在可捲動表格之外。 */
export function RuleCellLegend() {
  return (
    <div
      aria-label="稽核格圖例"
      className="shrink-0 border-t border-separator px-4 py-3 text-caption"
    >
      <ul className="flex flex-wrap gap-x-4 gap-y-2">
        {LEGEND.map(({ state, label }) => (
          <li key={state}>
            <RuleCellBadge
              cell={{
                rule_code: "",
                state,
                label,
                verdict: null,
                finding_count: 0,
              }}
            />
          </li>
        ))}
      </ul>
      <p className="mt-2 text-ink-secondary">
        數字為非紀錄完整的發現數；點選病患列可查看詳情。
      </p>
    </div>
  );
}
