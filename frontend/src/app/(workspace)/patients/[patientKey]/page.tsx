import Link from "next/link";
import { notFound } from "next/navigation";

import { CaretLeftIcon } from "@/components/ui/icons";
import { getPatientBed } from "@/lib/api/wards";
import { DEFAULT_WARD_CODE } from "@/lib/constants";

type PatientPageProps = {
  params: Promise<{ patientKey: string }>;
};

// TODO(待決): 病患頁面內容（病患摘要、各規則稽核結果、Evidence）待討論後實作
export default async function PatientPage({ params }: PatientPageProps) {
  const { patientKey } = await params;
  const bed = await getPatientBed(DEFAULT_WARD_CODE, patientKey);
  if (!bed) {
    notFound();
  }

  return (
    <div className="glass relative mx-auto mt-6 max-w-3xl rounded-panel p-6 shadow-float max-lg:mx-4 lg:mt-8">
      <Link
        href="/"
        className="-ml-2 inline-flex min-h-11 pressable items-center gap-1 rounded-xl px-2 text-body text-ink-secondary focus-ring hover:text-ink"
      >
        <CaretLeftIcon aria-hidden="true" className="size-4.5" />
        病房總覽
      </Link>
      <p className="mt-2 text-footnote font-semibold text-ink-secondary">
        {bed.bedCode}
      </p>
      <h1 className="text-large-title">{bed.patient.name}</h1>

      <section className="mt-8 rounded-panel bg-surface p-8 text-center shadow-card">
        <h2 className="text-headline">病患頁面建置中</h2>
        <p className="mt-2 text-body text-ink-secondary">
          病患摘要、各規則稽核結果與 Evidence 原文待討論後提供。
        </p>
      </section>
    </div>
  );
}
