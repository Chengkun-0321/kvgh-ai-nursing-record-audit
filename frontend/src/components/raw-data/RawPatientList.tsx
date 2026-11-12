import Link from "next/link";

import type { RawPatientList as RawPatientListData } from "@/lib/api/rawData";
import { formatShortDateTime } from "@/lib/format";
import { type RawDataSearch, rawDataHref } from "@/lib/rawDataQuery";
import { cn } from "@/lib/utils";

type RawPatientListProps = {
  data: RawPatientListData;
  search: RawDataSearch;
  selectedKey: string | null;
};

/** 左欄病人清單：床號、入院時間、工作清單完成度；不在最新名單的病人另外標示。 */
export function RawPatientList({
  data,
  search,
  selectedKey,
}: RawPatientListProps) {
  return (
    <nav
      aria-label="病人清單"
      className="flex flex-col gap-2 rounded-panel bg-surface p-3 shadow-card"
    >
      <p className="px-2 pt-1 text-footnote font-semibold text-ink-secondary">
        {data.display_name}・{data.patients.length} 位病人
      </p>
      <ul className="flex max-h-[40dvh] flex-col gap-1 overflow-y-auto lg:max-h-[calc(100dvh-12rem)]">
        {data.patients.map((patient) => {
          const isSelected = patient.patient_key === selectedKey;
          return (
            <li key={patient.patient_key}>
              <Link
                href={rawDataHref(search, {
                  patient: patient.patient_key,
                  sourceDate: null,
                })}
                aria-current={isSelected ? "page" : undefined}
                className={cn(
                  "flex min-h-11 flex-col rounded-xl px-3 py-2 focus-ring",
                  isSelected
                    ? "bg-accent-tint text-accent-strong"
                    : "hover:bg-fill",
                )}
              >
                <span className="flex items-center gap-2">
                  <span className="text-body font-semibold tabular-nums">
                    {patient.bed_code}
                  </span>
                  {!patient.is_current && (
                    <span className="rounded-full bg-fill px-2 text-caption text-ink-secondary">
                      已不在最新名單
                    </span>
                  )}
                </span>
                <span className="text-caption text-ink-secondary tabular-nums">
                  入院{" "}
                  {patient.admitted_at
                    ? formatShortDateTime(patient.admitted_at)
                    : "—"}
                  ・工作清單 {patient.work_checklist_filled_count}/
                  {patient.work_checklist_total_count}
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
