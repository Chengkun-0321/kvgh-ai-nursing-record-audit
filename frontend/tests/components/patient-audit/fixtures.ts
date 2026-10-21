// 測試用的虛構稽核資料（欄位依 boundaries.md 的 B1、B2）
import type {
  AuditDay,
  AuditFinding,
  Evidence,
  NoteSimilarity,
} from "@/types/patientAudit";

export const FIRST_DAY_REASON = "入院首日，無前日紀錄可比較";

export function makeSimilarity(
  overrides: Partial<NoteSimilarity> = {},
): NoteSimilarity {
  return {
    record_id: "NPN-B-0904-01",
    recorded_at: "2026-09-04T09:30:00+08:00",
    similar_record_id: "NPN-B-0903-01",
    similar_business_date: "2026-09-03",
    similarity_percent: 98,
    issue_types: ["copy"],
    ...overrides,
  };
}

export function makeEvidence(overrides: Partial<Evidence> = {}): Evidence {
  return {
    source: "nursing_progress_note",
    record_id: "NPN-B-0904-01",
    field: "content",
    recorded_at: "2026-09-04T09:30:00+08:00",
    excerpt: "虛構原文片段病人意識清楚",
    ...overrides,
  };
}

export function makeFinding(
  overrides: Partial<AuditFinding> = {},
): AuditFinding {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    audit_run_id: "00000000-0000-4000-8000-000000000101",
    rule_code: "R02",
    patient_key: "P001",
    business_date: "2026-09-04",
    verdict: "WARNING",
    message: "虛構稽核訊息甲，請確認",
    evidence: [makeEvidence()],
    note_similarities: [makeSimilarity()],
    engine: "llm",
    model: "fake-model-x",
    prompt_version: "r02_copy_paste/v1",
    system_prompt_version: 3,
    audited_at: "2026-09-05T10:00:00+08:00",
    ...overrides,
  };
}

export function makeDay(
  businessDate: string,
  overrides: Partial<AuditDay> = {},
): AuditDay {
  return {
    business_date: businessDate,
    admission_id: "ADM-P001-01",
    auditable: true,
    not_auditable_reason: null,
    latest_finding: null,
    ...overrides,
  };
}

// 三種卡片狀態各一天：不可稽核（9/01）、尚未稽核（9/02）、已稽核（9/04）
export const NOT_AUDITABLE_DAY = makeDay("2026-09-01", {
  auditable: false,
  not_auditable_reason: FIRST_DAY_REASON,
});
export const NOT_RUN_DAY = makeDay("2026-09-02");
export const DONE_DAY = makeDay("2026-09-04", {
  latest_finding: makeFinding(),
});
