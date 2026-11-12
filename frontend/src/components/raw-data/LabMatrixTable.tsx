import type { LabMatrix, LabMatrixValue } from "@/lib/api/rawData";
import { formatShortDateTime } from "@/lib/format";
import { LAB_FLAG_STYLES } from "@/lib/labFlags";
import { cn } from "@/lib/utils";

type LabMatrixTableProps = {
  matrix: LabMatrix;
};

/**
 * 檢驗總表：列為項目、欄為採檢時間（由舊到新），同一項目可橫向比較趨勢。
 * 項目欄固定在左側，欄位多時橫向捲動。
 */
export function LabMatrixTable({ matrix }: LabMatrixTableProps) {
  if (matrix.columns.length === 0) {
    return (
      <p className="rounded-card bg-canvas p-6 text-center text-body text-ink-secondary">
        這段時間內沒有檢驗報告
      </p>
    );
  }
  return (
    <div className="overflow-x-auto rounded-card bg-surface shadow-card">
      <table className="min-w-full text-footnote tabular-nums">
        <thead>
          <tr className="text-left text-ink-secondary">
            <th
              scope="col"
              className="sticky left-0 z-10 bg-surface px-3 py-2 font-semibold"
            >
              項目
            </th>
            <th scope="col" className="px-3 py-2 font-semibold">
              範圍
            </th>
            {matrix.columns.map((column) => (
              <th
                key={column.time_text}
                scope="col"
                className="px-3 py-2 font-semibold whitespace-nowrap"
              >
                {column.occurred_at
                  ? formatShortDateTime(column.occurred_at)
                  : column.time_text}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-separator">
          {matrix.rows.map((row) => (
            <tr key={row.item}>
              <th
                scope="row"
                className="sticky left-0 bg-surface px-3 py-1.5 text-left font-medium whitespace-nowrap"
              >
                {row.item}
              </th>
              <td className="px-3 py-1.5 text-ink-secondary">
                {/* 院方對同一項目給過不同範圍時全部列出 */}
                {row.reference_ranges.length > 0
                  ? row.reference_ranges.map((range) => (
                      <span key={range} className="block whitespace-nowrap">
                        {range}
                      </span>
                    ))
                  : "—"}
              </td>
              {row.cells.map((cell, index) => (
                <MatrixCell
                  key={matrix.columns[index]?.time_text}
                  cell={cell}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MatrixCell({ cell }: { cell: readonly LabMatrixValue[] }) {
  if (cell.length === 0) {
    return <td className="px-3 py-1.5 text-ink-secondary/60">·</td>;
  }
  // 同一採檢時間、同一項目有多個結果時逐行列出，不互相覆蓋
  return (
    <td className="px-3 py-1.5 whitespace-nowrap">
      {cell.map((result, index) => {
        const flag = result.abnormal_flag
          ? LAB_FLAG_STYLES[result.abnormal_flag]
          : null;
        return (
          <span key={index} className={cn("block", flag?.className)}>
            {result.value}
            {flag?.symbol && (
              <span aria-label={flag.label}> {flag.symbol}</span>
            )}
          </span>
        );
      })}
    </td>
  );
}
