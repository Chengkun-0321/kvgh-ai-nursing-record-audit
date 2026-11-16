import Link from "next/link";
import type { ReactNode } from "react";

import { CaretLeftIcon, FileTextIcon } from "@/components/ui/icons";
import { BUTTON_PRIMARY } from "@/components/ui/controlStyles";

type PatientAuditHeaderProps = {
  patientKey: string;
  /** 置中的內容（日期切換）。 */
  children: ReactNode;
  /** 排在原始資料連結前的操作（一鍵稽核）。 */
  actions: ReactNode;
};

/**
 * 病患稽核頁的頁首：返回病房總覽、日期切換、操作（一鍵稽核、原始資料連結）排成同一列；
 * 窄螢幕放不下三欄時，改為返回連結、操作、日期切換各一列。
 */
export function PatientAuditHeader({
  patientKey,
  children,
  actions,
}: PatientAuditHeaderProps) {
  return (
    <header className="grid items-center gap-3 lg:grid-cols-[1fr_auto_1fr]">
      <Link
        href="/"
        className="-ml-2 inline-flex min-h-11 w-fit pressable items-center gap-1 rounded-xl px-2 text-body text-ink-secondary focus-ring hover:text-ink"
      >
        <CaretLeftIcon aria-hidden="true" className="size-4.5" />
        病房總覽
      </Link>
      <div className="order-last lg:order-none">{children}</div>
      <div className="flex flex-wrap items-center gap-2 lg:flex-nowrap lg:justify-self-end">
        {actions}
        <Link
          href={`/raw-data?patient=${encodeURIComponent(patientKey)}`}
          className={`${BUTTON_PRIMARY} whitespace-nowrap`}
        >
          <FileTextIcon aria-hidden="true" className="size-4.5" />
          檢視原始資料
        </Link>
      </div>
    </header>
  );
}
