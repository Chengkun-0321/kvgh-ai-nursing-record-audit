import type { PatientAuditDay } from "@/lib/api/patientAudits";

type PatientAuditTitleProps = {
  day: PatientAuditDay;
};

/** 稽核區塊左上角的病患識別：病房、入院時間、床號。 */
export function PatientAuditTitle({ day }: PatientAuditTitleProps) {
  return (
    <div className="audit-title">
      <p className="text-footnote font-semibold text-ink-secondary">
        {day.ward_code} 病房・入院時間 {day.admitted_at_text ?? "—"}
      </p>
      <h1 className="text-large-title tabular-nums">{day.bed_code}</h1>
    </div>
  );
}
