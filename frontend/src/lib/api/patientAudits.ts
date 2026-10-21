import { apiJson } from "@/lib/api/client";
import type { AuditDays, AuditFinding } from "@/types/patientAudit";

// 錯誤一律為帶繁中訊息的 ApiError（後端 `detail` 原文），元件以 toErrorMessage 顯示
export { ApiError, toErrorMessage } from "@/lib/api/client";

const AUDIT_RULE_CODE = "R02";

/**
 * 取得病患每個有資料的業務日與最新稽核結果。
 * Server Component 直接連 `API_BASE_URL`，不快取（沿用 client.ts 的規則）。
 */
export async function getAuditDays(patientKey: string): Promise<AuditDays> {
  return apiJson<AuditDays>(
    `/api/v1/patients/${encodeURIComponent(patientKey)}/audit-days`,
  );
}

/**
 * 對病患的某一天執行稽核（瀏覽器呼叫同網域的 `/api/v1/audit-runs`）。
 * 後端會等模型判斷完成才回應。
 */
export async function runAudit(
  patientKey: string,
  businessDate: string,
): Promise<AuditFinding> {
  return apiJson<AuditFinding>("/api/v1/audit-runs", {
    method: "POST",
    body: JSON.stringify({
      patient_key: patientKey,
      business_date: businessDate,
      rule_code: AUDIT_RULE_CODE,
    }),
  });
}
