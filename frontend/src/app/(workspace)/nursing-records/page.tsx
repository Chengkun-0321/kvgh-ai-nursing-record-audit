import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { connection } from "next/server";

import { NursingRecordsView } from "@/components/nursing-records/NursingRecordsView";
import { PatientPicker } from "@/components/nursing-records/PatientPicker";
import { WarningCircleIcon } from "@/components/ui/icons";
import {
  loadNursingRecords,
  type NursingRecordsLoadResult,
} from "@/lib/api/mockDailyPackages";

export const metadata: Metadata = {
  title: "護理紀錄｜護理稽核系統",
};

type NursingRecordsPageProps = {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
};

const NOTICE_CLASS =
  "flex items-start gap-2 rounded-panel bg-surface p-5 text-body text-ink shadow-card";

function NursingRecordsContent({
  result,
}: {
  result: NursingRecordsLoadResult;
}) {
  if (!result.ok) {
    return (
      <p role="alert" className={NOTICE_CLASS}>
        <WarningCircleIcon
          aria-hidden="true"
          className="mt-0.5 size-5 shrink-0 text-danger"
        />
        {result.message}
      </p>
    );
  }
  if (!result.patient) {
    return <p className={NOTICE_CLASS}>目前沒有任何資料包。</p>;
  }
  return (
    <NursingRecordsView
      patientPicker={
        <PatientPicker
          patients={result.patients}
          selectedPatientId={result.patient.patientId}
        />
      }
      items={result.items}
    />
  );
}

// 每次開啟都重新讀取 mock_data/，修改 JSON 後重新整理即可看到
export default async function NursingRecordsPage({
  searchParams,
}: NursingRecordsPageProps) {
  await connection();
  const { patient: patientParam } = await searchParams;
  const requestedPatientId =
    typeof patientParam === "string" ? patientParam : undefined;
  const result = await loadNursingRecords(requestedPatientId);
  if (result.ok && requestedPatientId !== undefined && !result.patient) {
    notFound();
  }

  return (
    <div className="mx-auto flex max-w-[90rem] flex-col gap-4 px-4 pt-4 pb-8">
      <header>
        <p className="text-footnote font-semibold text-ink-secondary">
          {result.ok ? `${result.wardName}・` : ""}資料來源
          mock_data（完全虛構）
        </p>
        <h1 className="text-large-title">護理紀錄</h1>
        <p className="mt-1 text-body text-ink-secondary">
          選擇病患後，依時間由新到舊列出每天的紀錄；可勾選要看的紀錄類型。
        </p>
      </header>
      <NursingRecordsContent result={result} />
    </div>
  );
}
