"use client";

import { runAudit } from "@/lib/api/patientAudits";
import type { AuditDay } from "@/types/patientAudit";

import { DailyAuditList } from "./DailyAuditList";

type PatientDailyAuditsProps = {
  patientKey: string;
  days: AuditDay[];
};

/**
 * 病患頁的每日稽核清單入口：在 client 端注入 `runAudit`。
 * Server Component 不能把函式當 props 傳給 Client Component，所以由這一層（client）傳入。
 */
export function PatientDailyAudits({
  patientKey,
  days,
}: PatientDailyAuditsProps) {
  return (
    <DailyAuditList patientKey={patientKey} days={days} runAudit={runAudit} />
  );
}
