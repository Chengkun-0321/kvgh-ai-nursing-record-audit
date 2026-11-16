import {
  type Dispatch,
  type RefObject,
  type SetStateAction,
  useEffect,
  useRef,
  useState,
} from "react";

import { toErrorMessage } from "@/lib/api/client";
import { type PatientAuditDay, runPatientAudit } from "@/lib/api/patientAudits";
import {
  type AuditRuleView,
  type AuditScopeState,
  buildRuleViews,
  clearRunningFlags,
  emptyScopeState,
  isRunAllTarget,
  patchRule,
  type RuleRunState,
  scopeKeyOf,
  stateForScope,
} from "@/lib/patientAuditRunState";

export type { AuditRuleView } from "@/lib/patientAuditRunState";

export type AuditRunsHook = {
  /** 每項規則目前要顯示的結果與執行狀態，順序與總覽相同 */
  rules: AuditRuleView[];
  /** 執行單項規則；同一項執行中時不重複送出，失敗只影響該項 */
  runRule: (ruleCode: string) => Promise<void>;
  /** 同時送出所有可一鍵稽核且未在執行中的規則；後端自行限制併發 */
  runAll: () => Promise<void>;
  /** 是否有任何可一鍵稽核的項目 */
  canRunAll: boolean;
  /** 是否有任何可一鍵稽核的項目正在執行 */
  isRunningAll: boolean;
};

type RequestRegistry = RefObject<Map<string, AbortController>>;
type ScopeSetter = Dispatch<SetStateAction<AuditScopeState>>;

/**
 * 登記執行中的請求。範圍（病人或日期）改變、或元件卸載時全部中止，
 * 並清除執行中旗標；中止後的遲到回應不會再寫入狀態。
 */
function useRequestRegistry(
  scope: string,
  setState: ScopeSetter,
): RequestRegistry {
  const registry = useRef(new Map<string, AbortController>());

  useEffect(() => {
    const controllers = registry.current;
    return () => {
      for (const controller of controllers.values()) {
        controller.abort();
      }
      controllers.clear();
      setState((prev) => clearRunningFlags(prev, scope));
    };
  }, [scope, setState]);

  return registry;
}

/** 呼叫後端執行單項規則，回傳要寫入狀態的內容；中止時回傳 `null`（不寫入）。 */
async function fetchRunPatch(
  day: PatientAuditDay,
  ruleCode: string,
  signal: AbortSignal,
): Promise<Partial<RuleRunState> | null> {
  try {
    const run = await runPatientAudit(
      {
        patientKey: day.patient_key,
        businessDate: day.business_date,
        ruleCode,
      },
      signal,
    );
    return { run, isRunning: false, errorMessage: null };
  } catch (error) {
    if (signal.aborted) {
      return null;
    }
    return { isRunning: false, errorMessage: toErrorMessage(error) };
  }
}

function createRunRule(
  day: PatientAuditDay,
  setState: ScopeSetter,
  registry: RequestRegistry,
): AuditRunsHook["runRule"] {
  const scope = scopeKeyOf(day);
  return async (ruleCode) => {
    const requests = registry.current;
    if (requests.has(ruleCode)) {
      return;
    }
    const controller = new AbortController();
    requests.set(ruleCode, controller);
    setState((prev) =>
      patchRule(prev, scope, ruleCode, { isRunning: true, errorMessage: null }),
    );

    const patch = await fetchRunPatch(day, ruleCode, controller.signal);
    if (requests.get(ruleCode) === controller) {
      requests.delete(ruleCode);
    }
    if (patch && !controller.signal.aborted) {
      setState((prev) => patchRule(prev, scope, ruleCode, patch));
    }
  };
}

function createRunAll(
  day: PatientAuditDay,
  runRule: AuditRunsHook["runRule"],
  registry: RequestRegistry,
): AuditRunsHook["runAll"] {
  return async () => {
    const codes = day.rules
      .filter(
        (rule) => isRunAllTarget(rule) && !registry.current.has(rule.rule_code),
      )
      .map((rule) => rule.rule_code);
    await Promise.all(codes.map((code) => runRule(code)));
  };
}

/**
 * 病患稽核總覽的規則執行狀態。切換病人或日期（`day` 改變）時，
 * 執行中的請求會被中止，新總覽從伺服器的 `latest_run` 開始顯示。
 */
export function useAuditRuns(day: PatientAuditDay): AuditRunsHook {
  const scope = scopeKeyOf(day);
  const [state, setState] = useState(() => emptyScopeState(scope));
  const registry = useRequestRegistry(scope, setState);
  const runRule = createRunRule(day, setState, registry);
  const runAll = createRunAll(day, runRule, registry);

  const rules = buildRuleViews(day.rules, stateForScope(state, scope));
  const targets = rules.filter(isRunAllTarget);
  return {
    rules,
    runRule,
    runAll,
    canRunAll: targets.length > 0,
    isRunningAll: targets.some((rule) => rule.isRunning),
  };
}
