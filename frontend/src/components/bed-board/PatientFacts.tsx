import { formatDate } from "@/lib/format";
import type { PatientSummary } from "@/lib/api/wards";

type PatientFactsProps = {
  patient: PatientSummary;
};

const SEX_LABELS = { M: "男", F: "女" } as const;
// 院方資料沒有的欄位（目前姓名、性別、年齡、診斷皆無）
const MISSING = "—";

function describeAdmission(patient: PatientSummary): string {
  if (!patient.admission_date) {
    return MISSING;
  }
  const stay =
    patient.length_of_stay_days === null
      ? ""
      : `（住院 ${patient.length_of_stay_days} 天）`;
  return `${formatDate(patient.admission_date)}${stay}`;
}

/** 病患基本資料：姓名、性別、年齡、入院日與住院天數、診斷；數值由後端算好，缺的欄位顯示「—」。 */
export function PatientFacts({ patient }: PatientFactsProps) {
  const sexAndAge = [
    patient.sex ? SEX_LABELS[patient.sex] : null,
    patient.age_years === null ? null : `${patient.age_years} 歲`,
  ].filter(Boolean);

  return (
    <div>
      {(patient.name || sexAndAge.length > 0) && (
        <p className="flex items-baseline gap-3">
          {patient.name && <span className="text-title">{patient.name}</span>}
          {sexAndAge.length > 0 && (
            <span className="text-body text-ink-secondary">
              {sexAndAge.join("・")}
            </span>
          )}
        </p>
      )}
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-body first:mt-0">
        <dt className="text-ink-secondary">入院日</dt>
        <dd className="tabular-nums">{describeAdmission(patient)}</dd>
        <dt className="text-ink-secondary">診斷</dt>
        <dd>{patient.diagnosis ?? MISSING}</dd>
      </dl>
    </div>
  );
}
