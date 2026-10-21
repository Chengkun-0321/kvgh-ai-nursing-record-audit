import { VerdictIcon } from "@/components/VerdictIcon";
import { cn } from "@/lib/utils";
import { VERDICT_LABELS } from "@/lib/verdict";
import { VERDICT_STYLES } from "@/lib/verdictStyles";
import type { Verdict } from "@/types/patientAudit";

type AuditVerdictBadgeProps = {
  verdict: Verdict;
};

/** 判定徽章：顏色＋圖示＋文字，不只靠顏色表達狀態。 */
export function AuditVerdictBadge({ verdict }: AuditVerdictBadgeProps) {
  const style = VERDICT_STYLES[verdict];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-footnote font-semibold",
        style.tint,
        style.text,
      )}
    >
      <VerdictIcon verdict={verdict} className="size-4" />
      {VERDICT_LABELS[verdict]}
    </span>
  );
}
