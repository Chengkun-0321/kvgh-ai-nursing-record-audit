import type { AuditRuleView } from "@/hooks/useAuditRuns";
import type {
  AuditAvailability,
  AuditRun,
  AuditVerdict,
} from "@/lib/api/patientAudits";

/** 畫面上要呈現的狀態種類；verdict 以外的種類文字都來自後端回傳的欄位。 */
export type AuditDisplayKind =
  | "verdict"
  | "unaudited"
  | "not_applicable"
  | "unavailable"
  | "day_not_ended"
  | "failed"
  | "running";

export type AuditDisplay = {
  kind: AuditDisplayKind;
  /** 只有 kind 為 verdict 時有值 */
  verdict: AuditVerdict | null;
  label: string;
  /** 說明狀態原因（後端 reason／status_reason），沒有時為 null */
  reason: string | null;
};

const UNAUDITED: AuditDisplay = {
  kind: "unaudited",
  verdict: null,
  label: "尚未稽核",
  reason: null,
};

function fromRun(run: AuditRun): AuditDisplay {
  if (run.status === "COMPLETED" && run.verdict) {
    return {
      kind: "verdict",
      verdict: run.verdict,
      label: run.verdict_label ?? run.status_label,
      reason: null,
    };
  }
  const kind = run.status === "NOT_APPLICABLE" ? "not_applicable" : null;
  if (kind) {
    return {
      kind,
      verdict: null,
      label: run.status_label,
      reason: run.status_reason,
    };
  }
  const unavailable = run.status === "DATA_UNAVAILABLE";
  return {
    kind: unavailable ? "unavailable" : "failed",
    verdict: null,
    label: run.status_label,
    reason: run.status_reason,
  };
}

function fromAvailability(availability: AuditAvailability): AuditDisplay {
  if (availability.state === "not_applicable") {
    return {
      kind: "not_applicable",
      verdict: null,
      label: availability.label,
      reason: availability.reason,
    };
  }
  if (availability.state === "data_unavailable") {
    return {
      kind: "unavailable",
      verdict: null,
      label: availability.label,
      reason: availability.reason,
    };
  }
  if (availability.state === "day_not_ended") {
    return {
      kind: "day_not_ended",
      verdict: null,
      label: availability.label,
      reason: availability.reason,
    };
  }
  return UNAUDITED;
}

/** 規則目前應顯示的狀態：執行中優先，其次是最新結果，最後才是可稽核性。 */
export function resolveAuditDisplay(rule: AuditRuleView): AuditDisplay {
  if (rule.isRunning) {
    return { kind: "running", verdict: null, label: "稽核中", reason: null };
  }
  if (rule.displayedRun) {
    return fromRun(rule.displayedRun);
  }
  return fromAvailability(rule.availability);
}
