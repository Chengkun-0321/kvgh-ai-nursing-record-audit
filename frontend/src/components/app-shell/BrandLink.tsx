import Link from "next/link";

import { PlusIcon } from "@/components/ui/icons";
import { cn } from "@/lib/utils";

type BrandLinkProps = {
  className?: string;
  /** 桌機導覽較窄時只顯示標誌，文字改為 `sr-only` 仍可被螢幕閱讀器讀出 */
  labelClassName?: string;
};

/** 系統標誌＋名稱，連回病房總覽；手機放在頂列，桌機放在頂部導覽左側的玻璃膠囊。 */
export function BrandLink({ className, labelClassName }: BrandLinkProps) {
  return (
    <Link
      href="/"
      className={cn(
        "flex min-h-11 items-center gap-2.5 rounded-xl focus-ring",
        className,
      )}
    >
      <span className="grid size-9 shrink-0 place-items-center rounded-full bg-accent text-accent-contrast shadow-card">
        <PlusIcon weight="bold" aria-hidden="true" className="size-5" />
      </span>
      <span className={cn("text-headline whitespace-nowrap", labelClassName)}>
        護理稽核系統
      </span>
    </Link>
  );
}
