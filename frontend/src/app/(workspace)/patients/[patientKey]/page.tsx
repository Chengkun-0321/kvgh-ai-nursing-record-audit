import Link from "next/link";
import { notFound } from "next/navigation";

import { CaretLeftIcon } from "@/components/ui/icons";
import { ApiError } from "@/lib/api/client";
import { getRawPatientDetail, type RawPatientDetail } from "@/lib/api/rawData";

type PatientPageProps = {
  params: Promise<{ patientKey: string }>;
};

const NOT_FOUND_STATUS = 404;

async function loadPatient(patientKey: string): Promise<RawPatientDetail> {
  try {
    return await getRawPatientDetail(patientKey);
  } catch (error) {
    if (error instanceof ApiError && error.status === NOT_FOUND_STATUS) {
      notFound();
    }
    throw error;
  }
}

// TODO(待決): 病患頁面內容（病患摘要、各規則稽核結果、Evidence）待討論後實作
export default async function PatientPage({ params }: PatientPageProps) {
  const { patientKey } = await params;
  const patient = await loadPatient(patientKey);

  return (
    <div className="mx-auto mt-4 max-w-3xl rounded-panel bg-surface p-6 shadow-card max-lg:mx-4">
      <Link
        href="/"
        className="-ml-2 inline-flex min-h-11 pressable items-center gap-1 rounded-xl px-2 text-body text-ink-secondary focus-ring hover:text-ink"
      >
        <CaretLeftIcon aria-hidden="true" className="size-4.5" />
        病房總覽
      </Link>
      <p className="mt-2 text-footnote font-semibold text-ink-secondary">
        {patient.ward_code}
      </p>
      <h1 className="text-large-title tabular-nums">{patient.bed_code}</h1>

      <section className="mt-8 rounded-card bg-canvas p-8 text-center">
        <h2 className="text-headline">病患頁面建置中</h2>
        <p className="mt-2 text-body text-ink-secondary">
          病患摘要、各規則稽核結果與 Evidence 原文待討論後提供。
        </p>
        <Link
          href={`/raw-data?patient=${encodeURIComponent(patient.patient_key)}`}
          className="mt-4 inline-flex min-h-11 pressable items-center rounded-full bg-accent px-5 text-body font-semibold text-accent-contrast focus-ring"
        >
          檢視原始資料
        </Link>
      </section>
    </div>
  );
}
