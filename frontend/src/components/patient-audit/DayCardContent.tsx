import type { DayCardState } from "@/lib/dailyAudit";
import type { AuditFinding } from "@/types/patientAudit";

import { AuditFindingDetails } from "./AuditFindingDetails";

type DayCardContentProps = {
  state: DayCardState;
  notAuditableReason: string | null;
  finding: AuditFinding | null;
};

/** 卡片內容：依卡片狀態顯示不可稽核原因、「尚未稽核」或稽核結果。 */
export function DayCardContent({
  state,
  notAuditableReason,
  finding,
}: DayCardContentProps) {
  if (state === "not_auditable") {
    return <p className="text-body text-ink-secondary">{notAuditableReason}</p>;
  }
  if (state === "not_run" || finding === null) {
    return <p className="text-body text-ink-secondary">尚未稽核</p>;
  }
  return <AuditFindingDetails finding={finding} />;
}
