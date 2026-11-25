import {
  type Dispatch,
  type RefObject,
  type SetStateAction,
  useEffect,
  useRef,
  useState,
} from "react";

import { toErrorMessage } from "@/lib/api/client";
import {
  type AuditRuleStatus,
  getPatientAuditDay,
  type PatientAuditDay,
  runPatientAudit,
} from "@/lib/api/patientAudits";
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

/** 執行成功後重新取得的規則清單（含後端最新的 can_run）；只對應產生它的範圍。 */
type OverviewSnapshot = { scope: string; rules: AuditRuleStatus[] };
type OverviewSetter = Dispatch<SetStateAction<OverviewSnapshot | null>>;
type RefreshOverview = () => Promise<void>;

/** 重新讀取總覽的請求登記鍵；規則代號不會與之衝突。 */
const OVERVIEW_REQUEST_KEY = "__overview__";

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

/**
 * 範圍改變時丟棄舊範圍的總覽快照，避免切回原範圍時採用過期的規則清單。
 * 與 useRequestRegistry 相同的清理時機。
 */
function useOverviewReset(scope: string, setOverview: OverviewSetter): void {
  useEffect(() => {
    return () => {
      setOverview((prev) => (prev?.scope === scope ? null : prev));
    };
  }, [scope, setOverview]);
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

/**
 * 執行成功後重新讀取總覽，取得後端最新的 can_run 與 include_in_run_all
 * （例如入院規則完成後不再納入一鍵稽核）。讀取失敗時保留目前畫面。
 */
function createRefreshOverview(
  day: PatientAuditDay,
  setOverview: OverviewSetter,
  registry: RequestRegistry,
): RefreshOverview {
  const scope = scopeKeyOf(day);
  return async () => {
    const requests = registry.current;
    // 較新的讀取取代尚未完成的舊讀取，舊回應不會覆蓋新快照
    requests.get(OVERVIEW_REQUEST_KEY)?.abort();
    const controller = new AbortController();
    requests.set(OVERVIEW_REQUEST_KEY, controller);
    try {
      const fresh = await getPatientAuditDay(
        day.patient_key,
        day.business_date,
        controller.signal,
      );
      if (!controller.signal.aborted) {
        setOverview({ scope, rules: fresh.rules });
      }
    } catch {
      // 重新讀取失敗或已中止時不寫入；已顯示的結果保留，下次執行會再嘗試同步
    } finally {
      if (requests.get(OVERVIEW_REQUEST_KEY) === controller) {
        requests.delete(OVERVIEW_REQUEST_KEY);
      }
    }
  };
}

function createRunRule(
  day: PatientAuditDay,
  setState: ScopeSetter,
  registry: RequestRegistry,
  refreshOverview: RefreshOverview,
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
    if (patch?.run && !controller.signal.aborted) {
      void refreshOverview();
    }
  };
}

function createRunAll(
  rules: AuditRuleStatus[],
  runRule: AuditRunsHook["runRule"],
  registry: RequestRegistry,
): AuditRunsHook["runAll"] {
  return async () => {
    const codes = rules
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
  const [overview, setOverview] = useState<OverviewSnapshot | null>(null);
  const registry = useRequestRegistry(scope, setState);
  useOverviewReset(scope, setOverview);
  const refreshOverview = createRefreshOverview(day, setOverview, registry);
  const runRule = createRunRule(day, setState, registry, refreshOverview);

  const sourceRules = overview?.scope === scope ? overview.rules : day.rules;
  const runAll = createRunAll(sourceRules, runRule, registry);

  const rules = buildRuleViews(sourceRules, stateForScope(state, scope));
  const targets = rules.filter(isRunAllTarget);
  return {
    rules,
    runRule,
    runAll,
    canRunAll: targets.length > 0,
    isRunningAll: targets.some((rule) => rule.isRunning),
  };
}
