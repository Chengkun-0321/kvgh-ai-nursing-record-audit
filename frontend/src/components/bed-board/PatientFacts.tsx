import { formatDate } from "@/lib/format";
import { getLengthOfStayDays, SEX_LABELS } from "@/lib/patient";
import type { PatientSummary } from "@/types/ward";

type PatientFactsProps = {
  patient: PatientSummary;
  businessDate: string;
};

/** 病患基本資料：姓名、性別、年齡、入院日與住院天數、診斷。 */
export function PatientFacts({ patient, businessDate }: PatientFactsProps) {
  const lengthOfStayDays = getLengthOfStayDays(
    patient.admissionDate,
    businessDate,
  );

  return (
    <div>
      <p className="flex items-baseline gap-3">
        <span className="text-title">{patient.name}</span>
        <span className="text-body text-ink-secondary">
          {SEX_LABELS[patient.sex]}・{patient.ageYears} 歲
        </span>
      </p>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-body">
        <dt className="text-ink-secondary">入院日</dt>
        <dd className="tabular-nums">
          {formatDate(patient.admissionDate)}（住院 {lengthOfStayDays} 天）
        </dd>
        <dt className="text-ink-secondary">診斷</dt>
        <dd>{patient.diagnosis}</dd>
      </dl>
    </div>
  );
}
