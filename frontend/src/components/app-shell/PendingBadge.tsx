import { cn } from "@/lib/utils";

type PendingBadgeProps = {
  count: number;
  className?: string;
};

/** 紅色數字徽章；數量為 0 時不顯示。數字已由外層 aria-label 描述，故對輔助科技隱藏。 */
export function PendingBadge({ count, className }: PendingBadgeProps) {
  if (count === 0) {
    return null;
  }
  return (
    <span
      aria-hidden="true"
      className={cn(
        "inline-flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-badge px-1 text-caption font-semibold text-accent-contrast tabular-nums",
        className,
      )}
    >
      {count}
    </span>
  );
}
