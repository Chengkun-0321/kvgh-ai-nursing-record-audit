import type {
  AuditRuleStatus,
  AuditRun,
  PatientAuditDay,
} from "@/lib/api/patientAudits";

// useAuditRuns 測試共用的假資料；只供測試檔引用，不會進入正式頁面

export function makeRun(ruleCode: string, businessDate: string): AuditRun {
  return {
    id: `${ruleCode}-${businessDate}`,
    rule_code: ruleCode,
    rule_name: `規則 ${ruleCode}`,
    patient_key: "P001",
    business_date: businessDate,
    status: "COMPLETED",
    status_label: "已完成",
    status_reason: null,
    verdict: "PASS",
    verdict_label: "紀錄完整",
    summary: `${ruleCode} 結果`,
    findings: [],
    details: null,
    model: "test-model",
    prompt_version: 1,
    system_prompt_version: 1,
    duration_ms: 10,
    created_at: "2026-11-16T00:00:00Z",
  };
}

export function makeRule(
  ruleCode: string,
  overrides: Partial<AuditRuleStatus> = {},
): AuditRuleStatus {
  return {
    rule_code: ruleCode,
    name: `規則 ${ruleCode}`,
    description: "",
    cycle: "daily",
    cycle_label: "每日",
    effective_business_date: "2026-11-16",
    availability: { state: "available", label: "可執行", reason: null },
    can_run: true,
    include_in_run_all: true,
    is_running: false,
    latest_run: null,
    ...overrides,
  };
}

export function makeDay(
  businessDate: string,
  rules: AuditRuleStatus[],
): PatientAuditDay {
  return {
    patient_key: "P001",
    ward_code: "W63",
    bed_code: "01",
    admitted_at: null,
    admitted_at_text: null,
    business_date: businessDate,
    available_dates: [businessDate],
    previous_date: null,
    next_date: null,
    rules,
  };
}

export function deferred<T>(): {
  promise: Promise<T>;
  resolve: (value: T) => void;
} {
  let resolve: (value: T) => void = () => {};
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}
