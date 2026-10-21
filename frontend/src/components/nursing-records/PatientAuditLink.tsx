import Link from "next/link";

import { ListChecksIcon } from "@/components/ui/icons";
import { patientAuditPath } from "@/lib/dailyAudit";

type PatientAuditLinkProps = {
  patientId: string;
};

/** 前往病患每日稽核結果頁（`patient_key` 即院方 `patient_id`）。 */
export function PatientAuditLink({ patientId }: PatientAuditLinkProps) {
  return (
    <Link
      href={patientAuditPath(patientId)}
      className="inline-flex min-h-11 pressable items-center justify-center gap-2 rounded-full bg-accent px-5 text-body font-semibold text-accent-contrast focus-ring"
    >
      <ListChecksIcon aria-hidden="true" className="size-5" />
      查看稽核結果
    </Link>
  );
}
