import {
  CircleNotchIcon,
  ClockCountdownIcon,
  type Icon,
  MinusCircleIcon,
  ProhibitIcon,
  WarningOctagonIcon,
} from "@/components/ui/icons";
import { VerdictIcon } from "@/components/VerdictIcon";
import type { RuleCell, RuleCellState } from "@/lib/api/wards";
import { getRuleCellPresentation } from "@/lib/ruleCellPresentation";
import { cn } from "@/lib/utils";
import { VERDICT_STYLES } from "@/lib/verdictStyles";

const NEUTRAL_ICONS: Partial<Record<RuleCellState, Icon>> = {
  RUNNING: CircleNotchIcon,
  FAILED: WarningOctagonIcon,
  NOT_APPLICABLE: ProhibitIcon,
  DATA_UNAVAILABLE: MinusCircleIcon,
  DAY_NOT_ENDED: ClockCountdownIcon,
};

/** 依後端 state 顯示圖示與 label；只有判定使用 verdict 色，其餘維持中性色。 */
export function RuleCellBadge({ cell }: { cell: RuleCell }) {
  const { verdict, text, isRunning } = getRuleCellPresentation(cell);
  const NeutralIcon = NEUTRAL_ICONS[cell.state] ?? MinusCircleIcon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap",
        verdict ? VERDICT_STYLES[verdict].text : "text-ink-secondary",
      )}
      aria-label={
        cell.finding_count > 0
          ? `${cell.label}，${cell.finding_count} 項發現`
          : cell.label
      }
    >
      {verdict ? (
        <VerdictIcon verdict={verdict} className="size-4" />
      ) : (
        <NeutralIcon
          aria-hidden="true"
          className={cn(
            "size-4 shrink-0",
            isRunning && "motion-safe:animate-spin",
          )}
        />
      )}
      {text}
    </span>
  );
}
