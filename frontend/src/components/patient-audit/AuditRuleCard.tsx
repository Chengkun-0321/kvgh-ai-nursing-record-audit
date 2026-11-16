import type { AuditRuleView } from "@/hooks/useAuditRuns";
import { formatDate } from "@/lib/format";

import { AuditStatusBadge } from "./AuditStatusBadge";
import { resolveAuditDisplay } from "./auditDisplay";

type AuditRuleCardProps = {
  rule: AuditRuleView;
  /** 目前頁面的稽核日；與規則的 effective_business_date 不同時代表沿用入院當日等結果 */
  pageDate: string;
  onOpen: (ruleCode: string) => void;
  onRun: (ruleCode: string) => void;
};

const RUN_BUTTON_CLASS =
  "inline-flex min-h-11 shrink-0 pressable items-center rounded-full bg-accent-tint px-2 text-caption font-semibold text-accent-strong hover:bg-accent-tint-strong focus-ring disabled:opacity-45";

/** 單一稽核項目：代號、名稱、週期、狀態、稽核按鈕與錯誤訊息；點名稱開啟結果。 */
export function AuditRuleCard({
  rule,
  pageDate,
  onOpen,
  onRun,
}: AuditRuleCardProps) {
  const display = resolveAuditDisplay(rule);
  const isCarriedOver = rule.effective_business_date !== pageDate;
  const runLabel = rule.displayedRun ? "重新稽核" : "稽核";

  return (
    <li className="flex flex-col gap-1.5 rounded-card bg-surface p-2.5 shadow-card">
      <div className="flex min-w-0 items-center gap-2 text-caption text-ink-secondary">
        <span className="shrink-0 font-semibold tabular-nums">
          {rule.rule_code}
        </span>
        <span className="shrink-0 rounded-full bg-fill px-2 py-0.5">
          {rule.cycle_label}
        </span>
        {isCarriedOver && (
          <time
            dateTime={rule.effective_business_date}
            className="min-w-0 truncate tabular-nums"
          >
            {formatDate(rule.effective_business_date)}
          </time>
        )}
      </div>
      <button
        type="button"
        onClick={() => onOpen(rule.rule_code)}
        className="line-clamp-2 min-h-11 rounded-lg text-left text-headline focus-ring"
      >
        {rule.name}
      </button>
      <div className="flex min-h-11 items-center justify-between gap-1">
        <AuditStatusBadge display={display} className="flex-1" />
        {rule.can_run && (
          <button
            type="button"
            disabled={rule.isRunning}
            onClick={() => onRun(rule.rule_code)}
            aria-label={`${runLabel} ${rule.rule_code}`}
            className={RUN_BUTTON_CLASS}
          >
            {rule.isRunning ? "稽核中" : runLabel}
          </button>
        )}
      </div>
      {rule.errorMessage && (
        <p role="alert" className="line-clamp-1 text-caption text-danger">
          {rule.errorMessage}
        </p>
      )}
    </li>
  );
}
