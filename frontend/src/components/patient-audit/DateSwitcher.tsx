import Link from "next/link";

import { CaretLeftIcon, CaretRightIcon } from "@/components/ui/icons";
import { formatDate } from "@/lib/format";
import { patientAuditHref } from "@/lib/patientAuditQuery";
import { cn } from "@/lib/utils";

type DateSwitcherProps = {
  patientKey: string;
  businessDate: string;
  previousDate: string | null;
  nextDate: string | null;
};

const STEP_BASE =
  "inline-flex min-h-11 min-w-0 items-center justify-center gap-1 rounded-full px-2 text-body font-semibold focus-ring sm:px-4";
const STEP_ENABLED = "pressable bg-fill text-ink hover:bg-fill-strong";
// 沒有前後日時以停用樣式呈現，保留位置但不可點
const STEP_DISABLED = "bg-fill text-ink-secondary opacity-45";

/** 前一日／後一日以連結切換（網址即狀態）；目的地由後端給的日期決定。 */
export function DateSwitcher({
  patientKey,
  businessDate,
  previousDate,
  nextDate,
}: DateSwitcherProps) {
  return (
    <nav
      aria-label="切換稽核日期"
      className="grid grid-cols-[1fr_auto_1fr] items-center gap-2"
    >
      {previousDate ? (
        <Link
          href={patientAuditHref(patientKey, previousDate)}
          className={cn(STEP_BASE, STEP_ENABLED)}
        >
          <CaretLeftIcon aria-hidden="true" className="size-4.5" />
          前一日
        </Link>
      ) : (
        <span aria-disabled="true" className={cn(STEP_BASE, STEP_DISABLED)}>
          <CaretLeftIcon aria-hidden="true" className="size-4.5" />
          前一日
        </span>
      )}
      <p className="text-center text-headline tabular-nums">
        <time dateTime={businessDate}>{formatDate(businessDate)}</time>
      </p>
      {nextDate ? (
        <Link
          href={patientAuditHref(patientKey, nextDate)}
          className={cn(STEP_BASE, STEP_ENABLED)}
        >
          後一日
          <CaretRightIcon aria-hidden="true" className="size-4.5" />
        </Link>
      ) : (
        <span aria-disabled="true" className={cn(STEP_BASE, STEP_DISABLED)}>
          後一日
          <CaretRightIcon aria-hidden="true" className="size-4.5" />
        </span>
      )}
    </nav>
  );
}
