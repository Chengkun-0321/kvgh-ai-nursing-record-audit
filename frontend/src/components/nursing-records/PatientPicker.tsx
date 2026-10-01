import Link from "next/link";

import type { MockPatientSummary } from "@/lib/api/mockDailyPackages";
import { formatMonthDay } from "@/lib/format";
import { PATIENT_STATUS_LABELS } from "@/lib/nursingRecordFormat";
import { SEX_LABELS } from "@/lib/patient";
import { cn } from "@/lib/utils";

type PatientPickerProps = {
  patients: readonly MockPatientSummary[];
  selectedPatientId: string;
};

/**
 * 病患清單：桌機為左側直欄，手機為可橫向捲動的卡片列。
 * 以網址參數 `?patient=` 切換，重新整理或分享連結都會停在同一位病患。
 */
export function PatientPicker({
  patients,
  selectedPatientId,
}: PatientPickerProps) {
  return (
    <nav aria-label="病患">
      <ul className="-mx-4 flex [scrollbar-width:none] gap-2 overflow-x-auto px-4 py-1 lg:mx-0 lg:flex-col lg:overflow-visible lg:px-0">
        {patients.map((patient) => {
          const isSelected = patient.patientId === selectedPatientId;
          return (
            <li key={patient.patientId} className="shrink-0">
              <Link
                href={{
                  pathname: "/nursing-records",
                  query: { patient: patient.patientId },
                }}
                aria-current={isSelected ? "page" : undefined}
                className={cn(
                  "flex w-60 pressable flex-col gap-0.5 rounded-card px-4 py-3 focus-ring lg:w-auto",
                  isSelected ? "bg-surface shadow-card" : "hover:bg-fill",
                )}
              >
                <span className="flex items-baseline justify-between gap-2">
                  <span
                    className={cn(
                      "text-headline",
                      isSelected && "text-accent-strong",
                    )}
                  >
                    {patient.patientId}
                  </span>
                  <span className="text-footnote text-ink-secondary">
                    {patient.bedCode}・{PATIENT_STATUS_LABELS[patient.status]}
                  </span>
                </span>
                <span className="text-footnote">
                  {patient.ageYears} 歲{SEX_LABELS[patient.sex]}・
                  {patient.diagnosis}
                </span>
                <span className="text-caption text-ink-secondary tabular-nums">
                  資料 {formatMonthDay(patient.firstDate)}–
                  {formatMonthDay(patient.lastDate)}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
