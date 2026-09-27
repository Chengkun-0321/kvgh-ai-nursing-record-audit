import { VerdictIcon } from "@/components/VerdictIcon";
import { formatShortDateTime } from "@/lib/format";
import { getPendingFindings, VERDICT_LABELS } from "@/lib/verdict";
import type { AuditFindingSummary } from "@/types/ward";

type FindingListProps = {
  findings: readonly AuditFindingSummary[];
};

/** 詳情面板的稽核結果清單（依嚴重度排序）；完整 Evidence 於病患頁面呈現。 */
export function FindingList({ findings }: FindingListProps) {
  const pendingFindings = getPendingFindings(findings);

  if (pendingFindings.length === 0) {
    return (
      <p className="flex items-center gap-3 rounded-card bg-surface px-4 py-4 text-body shadow-card">
        <VerdictIcon verdict="PASS" />
        今日稽核項目皆無待確認事項
      </p>
    );
  }

  return (
    <ul className="divide-y divide-separator rounded-card bg-surface shadow-card">
      {pendingFindings.map((finding) => (
        <li
          key={`${finding.ruleCode}-${finding.recordedAt}`}
          className="flex gap-3 px-4 py-3"
        >
          <VerdictIcon verdict={finding.verdict} className="mt-0.5" />
          <div className="min-w-0 flex-1">
            <p className="text-body">{finding.message}</p>
            <p className="mt-1 text-caption text-ink-secondary">
              {finding.ruleCode}・{VERDICT_LABELS[finding.verdict]}
            </p>
          </div>
          <time
            dateTime={finding.recordedAt}
            className="shrink-0 text-footnote text-ink-secondary tabular-nums"
          >
            {formatShortDateTime(finding.recordedAt)}
          </time>
        </li>
      ))}
    </ul>
  );
}
