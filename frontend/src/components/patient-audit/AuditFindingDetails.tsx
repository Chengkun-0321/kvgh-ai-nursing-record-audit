import { formatAuditedAt, formatSimilarity } from "@/lib/dailyAudit";
import type { AuditFinding } from "@/types/patientAudit";

import { AuditVerdictBadge } from "./AuditVerdictBadge";
import { EvidenceList } from "./EvidenceList";

type AuditFindingDetailsProps = {
  finding: AuditFinding;
};

/** 一筆稽核結果：判定、訊息、逐筆相似度、Evidence、稽核時間與模型。 */
export function AuditFindingDetails({ finding }: AuditFindingDetailsProps) {
  return (
    <div className="flex flex-col gap-3">
      <div>
        <AuditVerdictBadge verdict={finding.verdict} />
      </div>
      <p className="text-body">{finding.message}</p>
      {finding.note_similarities.length > 0 ? (
        <ul
          aria-label="逐筆相似度"
          className="flex flex-col gap-1 text-footnote text-ink-secondary"
        >
          {finding.note_similarities.map((note) => (
            <li key={note.record_id}>{formatSimilarity(note)}</li>
          ))}
        </ul>
      ) : null}
      <EvidenceList evidence={finding.evidence} />
      <p className="text-caption text-ink-secondary tabular-nums">
        稽核時間 {formatAuditedAt(finding.audited_at)}
        {finding.model ? `・模型 ${finding.model}` : ""}
      </p>
    </div>
  );
}
