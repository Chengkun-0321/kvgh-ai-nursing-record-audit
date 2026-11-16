import Link from "next/link";
import { notFound } from "next/navigation";

import { PatientAuditBoard } from "@/components/patient-audit/PatientAuditBoard";
import { CaretLeftIcon, WarningCircleIcon } from "@/components/ui/icons";
import { loadPatientAuditDay } from "@/lib/api/patientAudits";
import { parseAuditDate } from "@/lib/patientAuditQuery";

type PatientAuditPageProps = {
  params: Promise<{ patientKey: string }>;
  searchParams: Promise<{ date?: string | string[] }>;
};

// 病患稽核頁：網址 `?date=YYYY-MM-DD` 即為狀態；未指定時由後端決定最新一日
export default async function PatientAuditPage({
  params,
  searchParams,
}: PatientAuditPageProps) {
  const { patientKey } = await params;
  const { date } = await searchParams;
  const result = await loadPatientAuditDay(
    patientKey,
    parseAuditDate(date) ?? undefined,
  );

  if (!result.ok) {
    if (result.reason === "not_found") {
      notFound();
    }
    return (
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 pt-4 pb-8 lg:px-8">
        <BackLink />
        <section
          role="alert"
          className="flex items-start gap-3 rounded-panel bg-surface p-6 text-body shadow-card"
        >
          <WarningCircleIcon
            aria-hidden="true"
            className="mt-0.5 size-5 shrink-0 text-danger"
          />
          <p>{result.message}</p>
        </section>
      </div>
    );
  }

  const { day } = result;
  return (
    <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 pt-4 pb-8 lg:px-8">
      <PatientAuditBoard
        key={`${day.patient_key}|${day.business_date}`}
        day={day}
      />
    </div>
  );
}

function BackLink() {
  return (
    <Link
      href="/"
      className="-ml-2 inline-flex min-h-11 w-fit pressable items-center gap-1 rounded-xl px-2 text-body text-ink-secondary focus-ring hover:text-ink"
    >
      <CaretLeftIcon aria-hidden="true" className="size-4.5" />
      病房總覽
    </Link>
  );
}
