// TODO(待決): 暫時手寫的稽核 API 型別（規格驅動流程無法啟動後端執行 gen:api），
// 收尾時改用 `npm run gen:api` 產生的 api.ts 型別並刪除本檔（比照 ADR 0010 的前例）

import type { Verdict } from "@/types/ward";

export type { Verdict };

/** 相似紀錄的問題類型。 */
export type IssueType =
  "copy" | "unchanged" | "clinical_changed" | "outdated_reference";

/** 判定依據：來源、紀錄 ID、欄位、時間、原文片段。 */
export type Evidence = {
  source: string;
  record_id: string;
  field: string | null;
  /** ISO 8601（帶時區） */
  recorded_at: string | null;
  excerpt: string | null;
};

/** 當日一筆護理過程紀錄與前日最相似紀錄的比對（相似度由模型估計）。 */
export type NoteSimilarity = {
  record_id: string;
  /** ISO 8601（帶時區） */
  recorded_at: string;
  similar_record_id: string | null;
  /** YYYY-MM-DD */
  similar_business_date: string | null;
  similarity_percent: number | null;
  issue_types: IssueType[];
};

/** 一筆稽核結果。 */
export type AuditFinding = {
  id: string;
  audit_run_id: string;
  rule_code: string;
  patient_key: string;
  /** YYYY-MM-DD */
  business_date: string;
  verdict: Verdict;
  message: string;
  evidence: Evidence[];
  note_similarities: NoteSimilarity[];
  engine: "rule" | "llm" | "hybrid";
  model: string | null;
  prompt_version: string | null;
  system_prompt_version: number | null;
  /** ISO 8601（帶時區） */
  audited_at: string;
};

/** 病患在一個業務日的稽核狀態。 */
export type AuditDay = {
  /** YYYY-MM-DD */
  business_date: string;
  admission_id: string;
  auditable: boolean;
  not_auditable_reason: string | null;
  latest_finding: AuditFinding | null;
};

/** 病患所有有資料的業務日。 */
export type AuditDays = {
  patient_key: string;
  days: AuditDay[];
};
