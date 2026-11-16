import { InfoIcon, XIcon } from "@/components/ui/icons";
import type { AuditRuleView } from "@/hooks/useAuditRuns";

import { AuditFindingItem } from "./AuditFindingItem";
import { AuditRunMeta } from "./AuditRunMeta";
import { AuditStatusBadge } from "./AuditStatusBadge";
import { resolveAuditDisplay } from "./auditDisplay";

type AuditResultBodyProps = {
  rule: AuditRuleView;
  titleId: string;
  onClose: () => void;
};

/** 結果視窗的內容：規則說明、判定與摘要、發現清單（含 Evidence）、執行資訊。 */
export function AuditResultBody({
  rule,
  titleId,
  onClose,
}: AuditResultBodyProps) {
  const display = resolveAuditDisplay(rule);
  const run = rule.displayedRun;
  const findings = run?.findings ?? [];

  return (
    <>
      <header className="flex shrink-0 items-start gap-3 px-5 pt-2 pb-3">
        <div className="min-w-0 flex-1">
          <p className="text-caption font-semibold text-ink-secondary">
            {rule.rule_code}・{rule.cycle_label}
          </p>
          <h2 id={titleId} className="text-title">
            {rule.name}
          </h2>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="關閉稽核結果"
          className="grid size-11 shrink-0 pressable place-items-center rounded-full text-ink-secondary focus-ring hover:bg-fill"
        >
          <XIcon aria-hidden="true" weight="bold" className="size-5" />
        </button>
      </header>
      <div className="overflow-y-auto overscroll-contain px-5 pb-[calc(env(safe-area-inset-bottom)+1.5rem)]">
        <AuditStatusBadge display={display} className="text-body" />
        <p className="mt-3 text-body text-ink-secondary">{rule.description}</p>
        {display.reason && (
          <p className="mt-4 flex gap-2 rounded-card bg-canvas p-3 text-footnote">
            <InfoIcon aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
            <span>{display.reason}</span>
          </p>
        )}
        {run?.summary && (
          <section aria-label="摘要" className="mt-5">
            <h3 className="text-headline">摘要</h3>
            <p className="mt-1.5 text-body whitespace-pre-wrap">
              {run.summary}
            </p>
          </section>
        )}
        {findings.length > 0 && (
          <section aria-label="發現清單" className="mt-5">
            <h3 className="text-headline">發現</h3>
            <ol className="mt-2 flex flex-col gap-3">
              {findings.map((finding) => (
                <AuditFindingItem key={finding.position} finding={finding} />
              ))}
            </ol>
          </section>
        )}
        {run && <AuditRunMeta run={run} />}
      </div>
    </>
  );
}
