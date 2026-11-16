import { VerdictIcon } from "@/components/VerdictIcon";
import {
  type Icon,
  CircleNotchIcon,
  MinusCircleIcon,
  ProhibitIcon,
  WarningCircleIcon,
  WarningOctagonIcon,
} from "@/components/ui/icons";
import { cn } from "@/lib/utils";
import { VERDICT_STYLES } from "@/lib/verdictStyles";

import type { AuditDisplay, AuditDisplayKind } from "./auditDisplay";

type AuditStatusBadgeProps = {
  display: AuditDisplay;
  className?: string;
};

// 圖示形狀與文字共同表意，顏色只是輔助（ui-design.md：不可只靠顏色）
const PHOSPHOR_ICONS: Record<AuditDisplayKind, Icon> = {
  verdict: WarningCircleIcon,
  unaudited: WarningCircleIcon,
  not_applicable: MinusCircleIcon,
  unavailable: ProhibitIcon,
  failed: WarningOctagonIcon,
  running: CircleNotchIcon,
};

const TEXT_CLASS: Record<AuditDisplayKind, string> = {
  verdict: "",
  unaudited: "text-ink-secondary",
  not_applicable: "text-ink-secondary",
  unavailable: "text-ink-secondary",
  failed: "text-danger",
  running: "text-accent-strong",
};

function StatusIcon({ display }: { display: AuditDisplay }) {
  if (display.verdict) {
    return <VerdictIcon verdict={display.verdict} className="size-4" />;
  }
  if (display.kind === "unaudited") {
    return <VerdictIcon verdict="NOT_AUDITED" className="size-4" />;
  }
  const PhosphorIcon = PHOSPHOR_ICONS[display.kind];
  return (
    <PhosphorIcon
      aria-hidden="true"
      className={cn(
        "size-4 shrink-0",
        display.kind === "running" && "motion-safe:animate-spin",
      )}
    />
  );
}

/** 稽核狀態：圖示＋文字（文字來自後端或暫定的判定字詞），顏色只作輔助。 */
export function AuditStatusBadge({
  display,
  className,
}: AuditStatusBadgeProps) {
  const textClass = display.verdict
    ? VERDICT_STYLES[display.verdict].text
    : TEXT_CLASS[display.kind];
  return (
    <span
      className={cn(
        "inline-flex min-w-0 items-center gap-1 text-footnote font-semibold",
        textClass,
        className,
      )}
    >
      <StatusIcon display={display} />
      <span className="truncate">{display.label}</span>
    </span>
  );
}
