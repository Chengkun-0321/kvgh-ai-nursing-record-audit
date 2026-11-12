import { VerdictIcon } from "@/components/VerdictIcon";
import type { AuditFindingSummary, BedBoardStatus } from "@/lib/api/wards";
import { formatShortDateTime } from "@/lib/format";

type FindingListProps = {
  /** 後端已排除 PASS、依嚴重度排序 */
  findings: readonly AuditFindingSummary[];
  /** 沒有待處理結果時顯示的文字與圖示狀態（由後端決定，例如「尚未稽核」） */
  emptyText: string;
  emptyStatus: BedBoardStatus;
};

/** 詳情面板的稽核結果清單；完整 Evidence 於病患頁面呈現。 */
export function FindingList({
  findings,
  emptyText,
  emptyStatus,
}: FindingListProps) {
  if (findings.length === 0) {
    return (
      <p className="flex items-center gap-3 rounded-card bg-surface px-4 py-4 text-body shadow-card">
        <VerdictIcon verdict={emptyStatus} />
        {emptyText}
      </p>
    );
  }

  return (
    <ul className="divide-y divide-separator rounded-card bg-surface shadow-card">
      {findings.map((finding) => (
        <li
          key={`${finding.rule_code}-${finding.recorded_at}`}
          className="flex gap-3 px-4 py-3"
        >
          <VerdictIcon verdict={finding.verdict} className="mt-0.5" />
          <div className="min-w-0 flex-1">
            <p className="text-body">{finding.message}</p>
            <p className="mt-1 text-caption text-ink-secondary">
              {finding.rule_code}・{finding.verdict_label}
            </p>
          </div>
          <time
            dateTime={finding.recorded_at}
            className="shrink-0 text-footnote text-ink-secondary tabular-nums"
          >
            {formatShortDateTime(finding.recorded_at)}
          </time>
        </li>
      ))}
    </ul>
  );
}
