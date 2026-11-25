import type { WardBedBoard } from "@/lib/api/wards";

import { RuleCellLegend } from "./RuleCellLegend";
import { WardPatientRow } from "./WardPatientRow";
import { WARD_TITLE_ID } from "./WardTitle";

type WardPatientListProps = {
  board: WardBedBoard;
  selectedBedCode?: string;
  onToggle: (bedCode: string) => void;
};

/** 一位病患一列、七項結果並排；窄畫面可水平捲動，床號與表頭固定。 */
export function WardPatientList({
  board,
  selectedBedCode,
  onToggle,
}: WardPatientListProps) {
  return (
    <section className="patient-list pointer-events-auto absolute inset-4 flex min-w-0 flex-col overflow-hidden rounded-card bg-surface shadow-card">
      <div
        role="region"
        aria-label="病患稽核清單，可水平與垂直捲動"
        tabIndex={0}
        className="min-h-0 flex-1 overflow-auto overscroll-contain focus-ring"
      >
        <table
          aria-labelledby={WARD_TITLE_ID}
          className="w-full border-separate border-spacing-0 text-footnote whitespace-nowrap"
        >
          <caption className="sr-only">
            病患清單與七項稽核狀態；Enter 或空白鍵開啟病床詳情。
          </caption>
          <thead className="sticky top-0 z-20 bg-surface text-ink-secondary">
            <tr className="h-11">
              <th
                scope="col"
                className="sticky left-0 z-30 bg-surface px-3 py-2 text-left"
              >
                床號
              </th>
              <th scope="col" className="px-3 py-2 text-left">
                入院日
              </th>
              <th scope="col" className="px-3 py-2 text-left">
                住院天數
              </th>
              {board.rules.map((rule) => (
                <th
                  key={rule.rule_code}
                  scope="col"
                  title={`${rule.rule_code} ${rule.name}`}
                  aria-label={`${rule.rule_code} ${rule.name}`}
                  className="px-3 py-2 text-left"
                >
                  {rule.short_name}
                </th>
              ))}
              <th scope="col" className="px-3 py-2 text-left">
                摘要
              </th>
            </tr>
          </thead>
          <tbody className="[&_td]:border-t [&_td]:border-separator [&_th]:border-t [&_th]:border-separator">
            {board.beds.map((bed) => (
              <WardPatientRow
                key={bed.bed_code}
                bed={bed}
                isSelected={bed.bed_code === selectedBedCode}
                onToggle={onToggle}
              />
            ))}
            {board.beds.length === 0 && (
              <tr>
                <td
                  colSpan={board.rules.length + 4}
                  className="p-8 text-center text-ink-secondary"
                >
                  目前沒有床位資料
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <RuleCellLegend />
    </section>
  );
}
