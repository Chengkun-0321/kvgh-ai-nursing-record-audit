import Link from "next/link";

import { CaretRightIcon, UserIcon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";

type PatientPageLinkProps = {
  patientKey: string;
  className?: string;
};

/** 病床詳情的主要操作：進入病患個人頁面。 */
export function PatientPageLink({
  patientKey,
  className,
}: PatientPageLinkProps) {
  return (
    <Link
      href={`/patients/${encodeURIComponent(patientKey)}`}
      className={cn(
        "flex min-h-14 pressable items-center gap-3 rounded-xl bg-accent px-5 text-headline text-accent-contrast focus-ring",
        className,
      )}
    >
      <UserIcon aria-hidden="true" className="size-5" />
      <span className="flex-1">進入病人個人頁面</span>
      <CaretRightIcon aria-hidden="true" className="size-4.5" />
    </Link>
  );
}
