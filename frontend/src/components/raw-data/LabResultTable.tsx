import type { TimelineEvent } from "@/lib/api/rawData";
import { LAB_FLAG_STYLES } from "@/lib/labFlags";

type LabResultTableProps = {
  results: TimelineEvent["lab_results"];
};

/** 同一次採檢的檢驗結果；異常值以「↑／↓＋顏色」標示，範圍沿用院方原文。 */
export function LabResultTable({ results }: LabResultTableProps) {
  return (
    <table className="w-full text-footnote">
      <thead className="text-left text-ink-secondary">
        <tr>
          <th scope="col" className="py-1 pr-3 font-semibold">
            項目
          </th>
          <th scope="col" className="py-1 pr-3 font-semibold">
            結果
          </th>
          <th scope="col" className="py-1 font-semibold">
            範圍
          </th>
        </tr>
      </thead>
      <tbody className="divide-y divide-separator">
        {results.map((result, index) => {
          const flag = result.abnormal_flag
            ? LAB_FLAG_STYLES[result.abnormal_flag]
            : null;
          return (
            <tr key={`${result.item}-${index}`}>
              <th scope="row" className="py-1.5 pr-3 text-left font-medium">
                {result.item}
              </th>
              <td
                className={`py-1.5 pr-3 tabular-nums ${flag?.className ?? ""}`}
              >
                {result.value}
                {flag?.symbol && (
                  <span aria-label={flag.label}> {flag.symbol}</span>
                )}
              </td>
              <td className="py-1.5 text-ink-secondary tabular-nums">
                {result.reference_range ?? "—"}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
