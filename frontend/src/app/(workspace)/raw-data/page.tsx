import type { Metadata } from "next";

import { RawPatientContent } from "@/components/raw-data/RawPatientContent";
import { RawPatientList } from "@/components/raw-data/RawPatientList";
import { listRawPatients } from "@/lib/api/rawData";
import { getDefaultWardCode } from "@/lib/api/wards";
import {
  parseRawDataSearch,
  type SearchParamsRecord,
} from "@/lib/rawDataQuery";

export const metadata: Metadata = {
  title: "原始資料｜護理稽核系統",
};

type RawDataPageProps = {
  searchParams: Promise<SearchParamsRecord>;
};

/** 原始資料：檢視院方每日傳送的病人資料，所有日期由後端合併成時間軸。 */
export default async function RawDataPage({ searchParams }: RawDataPageProps) {
  const search = parseRawDataSearch(await searchParams);
  const patients = await listRawPatients(await getDefaultWardCode());
  // 未指定病人時，預設為最新名單中的第一床
  const patientKey =
    search.patient ??
    patients.patients.find((patient) => patient.is_current)?.patient_key ??
    null;

  return (
    <div className="mx-auto flex max-w-[90rem] flex-col gap-4 px-4 pt-4 pb-8 lg:grid lg:grid-cols-[18rem_minmax(0,1fr)] lg:items-start lg:gap-6">
      <div className="lg:sticky lg:top-[calc(var(--spacing-toolbar)+1rem)]">
        <RawPatientList
          data={patients}
          search={search}
          selectedKey={patientKey}
        />
      </div>
      <div className="min-w-0">
        {patientKey ? (
          <RawPatientContent patientKey={patientKey} search={search} />
        ) : (
          <p className="rounded-panel bg-surface p-6 text-body shadow-card">
            這個病房目前沒有院方資料。
          </p>
        )}
      </div>
    </div>
  );
}
