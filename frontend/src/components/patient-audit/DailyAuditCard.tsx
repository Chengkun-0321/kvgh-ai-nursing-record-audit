"use client";

import { useState } from "react";

import { WarningCircleIcon } from "@/components/ui/icons";
import { toErrorMessage } from "@/lib/api/patientAudits";
import {
  auditButtonLabel,
  dayCardState,
  formatBusinessDate,
} from "@/lib/dailyAudit";
import type { AuditDay, AuditFinding } from "@/types/patientAudit";

import { DayCardContent } from "./DayCardContent";

/** 執行稽核的函式（由上層注入，測試可替換）。 */
export type RunAudit = (
  patientKey: string,
  businessDate: string,
) => Promise<AuditFinding>;

type DailyAuditCardProps = {
  patientKey: string;
  day: AuditDay;
  runAudit: RunAudit;
};

/**
 * 一個業務日的稽核卡片；各卡的請求狀態獨立。
 * 成功時以回傳結果更新本卡（不重新整理頁面），失敗時保留原本的結果並顯示錯誤訊息。
 */
export function DailyAuditCard({
  patientKey,
  day,
  runAudit,
}: DailyAuditCardProps) {
  const [finding, setFinding] = useState(day.latest_finding);
  const [isRunning, setIsRunning] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const currentDay: AuditDay = { ...day, latest_finding: finding };
  const buttonLabel = auditButtonLabel(currentDay, isRunning);

  async function handleRun() {
    setIsRunning(true);
    setErrorMessage(null);
    try {
      setFinding(await runAudit(patientKey, day.business_date));
    } catch (error) {
      setErrorMessage(toErrorMessage(error));
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <article
      data-business-date={day.business_date}
      aria-busy={isRunning}
      className="flex flex-col gap-4 rounded-card bg-surface p-5 shadow-card"
    >
      <header className="flex items-center justify-between gap-3">
        <h2 className="text-title tabular-nums">
          {formatBusinessDate(day.business_date)}
        </h2>
        {buttonLabel === null ? null : (
          <button
            type="button"
            onClick={handleRun}
            disabled={isRunning}
            className="inline-flex min-h-11 pressable items-center rounded-full bg-accent px-5 text-body font-semibold text-accent-contrast focus-ring disabled:opacity-60"
          >
            {buttonLabel}
          </button>
        )}
      </header>
      <DayCardContent
        state={dayCardState(currentDay)}
        notAuditableReason={day.not_auditable_reason}
        finding={finding}
      />
      {errorMessage === null ? null : (
        <p
          role="alert"
          className="flex items-start gap-2 rounded-card bg-danger-tint px-4 py-3 text-body text-danger"
        >
          <WarningCircleIcon
            aria-hidden="true"
            className="mt-0.5 size-5 shrink-0"
          />
          {errorMessage}
        </p>
      )}
    </article>
  );
}
