import type {
  AuditRun,
  AuditRuleStatus,
  PatientAuditDay,
} from "@/lib/api/patientAudits";

/** 單一規則在某次總覽中的執行狀態。 */
export type RuleRunState = {
  /** 成功執行後的新結果；未執行過時為 `null`（畫面改顯示 `latest_run`） */
  run: AuditRun | null;
  isRunning: boolean;
  errorMessage: string | null;
};

/**
 * 執行狀態所屬的範圍（病人＋稽核日期）。範圍不同時，舊狀態視為不存在，
 * 避免切換日期後仍顯示前一天的執行結果。
 */
export type AuditScopeState = {
  scope: string;
  rules: Record<string, RuleRunState>;
};

/**
 * 每項規則目前要顯示的內容：伺服器載入的規則資訊加上本地執行狀態。
 * `isRunning` 為本頁送出的請求尚未回應，或後端回報該項正在稽核中（重新整理、切換日期後仍保留）。
 */
export type AuditRuleView = AuditRuleStatus & {
  displayedRun: AuditRun | null;
  isRunning: boolean;
  errorMessage: string | null;
};

const IDLE_RULE_STATE: RuleRunState = {
  run: null,
  isRunning: false,
  errorMessage: null,
};

export function scopeKeyOf(day: PatientAuditDay): string {
  return `${day.patient_key}|${day.business_date}`;
}

export function emptyScopeState(scope: string): AuditScopeState {
  return { scope, rules: {} };
}

/** 只回傳屬於 `scope` 的狀態；其他範圍的狀態視為空。 */
export function stateForScope(
  state: AuditScopeState,
  scope: string,
): AuditScopeState {
  return state.scope === scope ? state : emptyScopeState(scope);
}

/** 更新單一規則的狀態；舊範圍的狀態會先被丟棄。 */
export function patchRule(
  state: AuditScopeState,
  scope: string,
  ruleCode: string,
  patch: Partial<RuleRunState>,
): AuditScopeState {
  const base = stateForScope(state, scope);
  const current = base.rules[ruleCode] ?? IDLE_RULE_STATE;
  return {
    scope,
    rules: { ...base.rules, [ruleCode]: { ...current, ...patch } },
  };
}

/** 範圍中止時清除所有「執行中」旗標，避免切回來時按鈕永遠停用。 */
export function clearRunningFlags(
  state: AuditScopeState,
  scope: string,
): AuditScopeState {
  if (state.scope !== scope) {
    return state;
  }
  const rules = Object.fromEntries(
    Object.entries(state.rules).map(([code, rule]) => [
      code,
      { ...rule, isRunning: false },
    ]),
  );
  return { scope, rules };
}

/** 一鍵稽核的對象：規則標示納入一鍵稽核，且目前可執行。 */
export function isRunAllTarget(rule: AuditRuleStatus): boolean {
  return rule.include_in_run_all && rule.can_run;
}

export function buildRuleViews(
  rules: AuditRuleStatus[],
  state: AuditScopeState,
): AuditRuleView[] {
  return rules.map((rule) => {
    const runState = state.rules[rule.rule_code];
    return {
      ...rule,
      displayedRun: runState?.run ?? rule.latest_run,
      isRunning: (runState?.isRunning ?? false) || rule.is_running,
      errorMessage: runState?.errorMessage ?? null,
    };
  });
}
