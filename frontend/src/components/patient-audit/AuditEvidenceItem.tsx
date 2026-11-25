import type { AuditEvidence } from "@/lib/api/patientAudits";
import { formatDate } from "@/lib/format";

type AuditEvidenceItemProps = {
  evidence: AuditEvidence;
};

/**
 * 單筆 Evidence：來源（後端給的繁中名稱）、欄位、該筆紀錄的日期與時間、原文片段。
 * 同一段原文可能出現在不同日期的紀錄，因此一定顯示該筆紀錄的時間或日期。
 */
export function AuditEvidenceItem({ evidence }: AuditEvidenceItemProps) {
  const excerpt = evidence.excerpt.trim();
  return (
    <li className="rounded-xl bg-surface p-3">
      {/* 來源與時間同一行（時間靠右），窄螢幕放不下時時間換到下一行 */}
      <p className="flex flex-wrap items-baseline justify-between gap-x-3">
        <span className="text-footnote font-semibold">
          {evidence.source_label}
          {evidence.field && (
            <span className="font-normal text-ink-secondary">
              ・{evidence.field}
            </span>
          )}
        </span>
        {/* 院方原始時間字串已含日期；沒有時才退回紀錄的日期 */}
        <time
          dateTime={evidence.business_date}
          className="text-caption text-ink-secondary tabular-nums"
        >
          {evidence.time_text || formatDate(evidence.business_date)}
        </time>
      </p>
      {excerpt ? (
        <blockquote className="mt-2 border-l-2 border-accent pl-3 text-body whitespace-pre-wrap">
          {excerpt}
        </blockquote>
      ) : (
        <p className="mt-2 text-footnote text-ink-secondary">（無原文片段）</p>
      )}
    </li>
  );
}
