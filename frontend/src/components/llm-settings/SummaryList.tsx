import type { SummaryRow } from "@/lib/llmConfigSummary";

type SummaryListProps = {
  rows: readonly SummaryRow[];
};

/** 設定摘要：實色卡片內的「欄位—值」清單。 */
export function SummaryList({ rows }: SummaryListProps) {
  return (
    <dl className="divide-y divide-separator rounded-card bg-surface px-4 shadow-card">
      {rows.map((row) => (
        <div key={row.label} className="flex gap-4 py-3">
          <dt className="w-24 shrink-0 text-footnote font-semibold text-ink-secondary">
            {row.label}
          </dt>
          <dd className="min-w-0 flex-1 text-body break-words text-ink">
            {row.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}
