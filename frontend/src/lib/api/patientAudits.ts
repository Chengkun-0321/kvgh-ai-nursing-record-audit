import type { components } from "@/types/api";

import { ApiError, apiJson, toErrorMessage } from "./client";

export type PatientAuditDay = components["schemas"]["PatientAuditDayRead"];
export type AuditRuleStatus = components["schemas"]["AuditRuleStatusRead"];
export type AuditRun = components["schemas"]["AuditRunRead"];
export type AuditRunStatus = components["schemas"]["AuditRunStatus"];
export type AuditFinding = components["schemas"]["AuditFindingRead"];
export type AuditEvidence = components["schemas"]["Evidence"];
export type AuditAvailability = components["schemas"]["AvailabilityRead"];
export type AuditCycle = components["schemas"]["AuditCycle"];
export type AuditVerdict = components["schemas"]["Verdict"];

/** 單一規則執行的輸入；`businessDate` 為畫面上的稽核日期（YYYY-MM-DD）。 */
export type RunPatientAuditInput = {
  patientKey: string;
  businessDate: string;
  ruleCode: string;
};

/** Server Component 載入結果：404 以 `reason` 回傳，讓頁面自行呼叫 `notFound()`。 */
export type PatientAuditDayResult =
  | { ok: true; day: PatientAuditDay }
  | { ok: false; reason: "not_found" }
  | { ok: false; reason: "error"; message: string };

const NOT_FOUND_STATUS = 404;

function auditsPath(patientKey: string): string {
  return `/api/v1/patients/${encodeURIComponent(patientKey)}/audits`;
}

/** 病患某日的稽核總覽；未指定日期時由後端回傳病人最新一天。 */
export function getPatientAuditDay(
  patientKey: string,
  businessDate?: string,
  signal?: AbortSignal,
): Promise<PatientAuditDay> {
  const query = businessDate
    ? `?${new URLSearchParams({ business_date: businessDate })}`
    : "";
  return apiJson<PatientAuditDay>(`${auditsPath(patientKey)}${query}`, {
    signal,
  });
}

/** 執行一項稽核規則並回傳結果；可能耗時數十秒（LLM 呼叫）。 */
export function runPatientAudit(
  { patientKey, businessDate, ruleCode }: RunPatientAuditInput,
  signal?: AbortSignal,
): Promise<AuditRun> {
  const path = `${auditsPath(patientKey)}/${encodeURIComponent(businessDate)}/rules/${encodeURIComponent(ruleCode)}/runs`;
  return apiJson<AuditRun>(path, { method: "POST", signal });
}

/**
 * Server Component 用的載入函式：不拋出錯誤，讓整頁不因單一請求失敗而炸掉。
 * 404 回傳 `reason: "not_found"`；頁面必須在 `try` 之外呼叫 `notFound()`，
 * 因為 `notFound()` 本身會拋出例外。其他錯誤回傳可顯示的繁中訊息。
 */
export async function loadPatientAuditDay(
  patientKey: string,
  businessDate?: string,
): Promise<PatientAuditDayResult> {
  try {
    return {
      ok: true,
      day: await getPatientAuditDay(patientKey, businessDate),
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === NOT_FOUND_STATUS) {
      return { ok: false, reason: "not_found" };
    }
    return { ok: false, reason: "error", message: toErrorMessage(error) };
  }
}
