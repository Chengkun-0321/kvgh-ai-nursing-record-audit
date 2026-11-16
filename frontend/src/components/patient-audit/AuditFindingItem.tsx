import { VerdictIcon } from "@/components/VerdictIcon";
import type { AuditFinding } from "@/lib/api/patientAudits";
import { VERDICT_STYLES } from "@/lib/verdictStyles";
import { cn } from "@/lib/utils";

import { AuditEvidenceItem } from "./AuditEvidenceItem";

type AuditFindingItemProps = {
  finding: AuditFinding;
};

/** 單筆發現：項目、判定（圖示＋文字）、說明與其 Evidence 清單。 */
export function AuditFindingItem({ finding }: AuditFindingItemProps) {
  const style = VERDICT_STYLES[finding.verdict];
  return (
    <li className="rounded-card bg-canvas p-4">
      <div className="flex items-start gap-2.5">
        <VerdictIcon verdict={finding.verdict} className="mt-0.5" />
        <div className="min-w-0 flex-1">
          <p className="text-headline">{finding.item}</p>
          <p className={cn("mt-0.5 text-footnote font-semibold", style.text)}>
            {finding.verdict_label}
          </p>
        </div>
      </div>
      <p className="mt-2.5 text-body whitespace-pre-wrap">{finding.message}</p>
      {finding.evidence.length > 0 && (
        <ul className="mt-3 flex flex-col gap-2">
          {finding.evidence.map((evidence, index) => (
            <AuditEvidenceItem
              key={`${evidence.record_id}-${evidence.field ?? ""}-${index}`}
              evidence={evidence}
            />
          ))}
        </ul>
      )}
    </li>
  );
}
