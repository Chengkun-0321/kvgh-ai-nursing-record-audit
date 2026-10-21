"use client";

import { sortDaysDesc } from "@/lib/dailyAudit";
import type { AuditDay } from "@/types/patientAudit";

import { DailyAuditCard, type RunAudit } from "./DailyAuditCard";

type DailyAuditListProps = {
  patientKey: string;
  days: AuditDay[];
  runAudit: RunAudit;
};

/** 每日稽核卡片清單：每個有資料的業務日一張，由新到舊排列。 */
export function DailyAuditList({
  patientKey,
  days,
  runAudit,
}: DailyAuditListProps) {
  if (days.length === 0) {
    return (
      <p className="rounded-card bg-canvas p-6 text-body text-ink-secondary">
        此病患目前沒有任何資料日。
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      {sortDaysDesc(days).map((day) => (
        <DailyAuditCard
          key={day.business_date}
          patientKey={patientKey}
          day={day}
          runAudit={runAudit}
        />
      ))}
    </div>
  );
}
