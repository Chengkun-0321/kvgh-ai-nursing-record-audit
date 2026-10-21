import Link from "next/link";

import { AuditDaysLoadError } from "@/components/patient-audit/AuditDaysLoadError";
import { PatientDailyAudits } from "@/components/patient-audit/PatientDailyAudits";
import { CaretLeftIcon } from "@/components/ui/icons";
import { getAuditDays } from "@/lib/api/patientAudits";
import { decodePatientKey } from "@/lib/dailyAudit";
import type { AuditDays } from "@/types/patientAudit";

type PatientPageProps = {
  params: Promise<{ patientKey: string }>;
};

async function loadAuditDays(patientKey: string): Promise<AuditDays | null> {
  try {
    return await getAuditDays(patientKey);
  } catch {
    // 錯誤訊息由 AuditDaysLoadError 統一呈現，不顯示任何卡片
    return null;
  }
}

/** 病患頁：依業務日期列出 R02 每日稽核結果，可對單日執行稽核。 */
export default async function PatientPage({ params }: PatientPageProps) {
  const { patientKey: rawPatientKey } = await params;
  const patientKey = decodePatientKey(rawPatientKey);
  const auditDays = await loadAuditDays(patientKey);

  return (
    <div className="mx-auto mt-4 flex max-w-3xl flex-col gap-4 pb-8 max-lg:mx-4">
      <Link
        href={{ pathname: "/nursing-records", query: { patient: patientKey } }}
        className="-ml-2 inline-flex min-h-11 pressable items-center gap-1 self-start rounded-xl px-2 text-body text-ink-secondary focus-ring hover:text-ink"
      >
        <CaretLeftIcon aria-hidden="true" className="size-4.5" />
        護理紀錄
      </Link>
      <header>
        <p className="text-footnote font-semibold text-ink-secondary">
          {patientKey}
        </p>
        <h1 className="text-large-title">每日稽核結果</h1>
        <p className="mt-1 text-body text-ink-secondary">
          比對當日與最近幾個有資料日的護理過程紀錄，提醒可能沿用前日內容或引用非當日資料的情形；相似度為模型估計。
        </p>
      </header>
      {auditDays === null ? (
        <AuditDaysLoadError patientKey={patientKey} />
      ) : (
        <PatientDailyAudits patientKey={patientKey} days={auditDays.days} />
      )}
    </div>
  );
}
