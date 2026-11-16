import type { AuditRun } from "@/lib/api/patientAudits";
import { formatDateTime } from "@/lib/format";

type AuditRunMetaProps = {
  run: AuditRun;
};

/** 執行資訊（次要）：稽核時間、模型與 prompt 版本。 */
export function AuditRunMeta({ run }: AuditRunMetaProps) {
  return (
    <dl className="mt-6 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 border-t border-separator pt-4 text-footnote">
      <dt className="text-ink-secondary">稽核時間</dt>
      <dd className="tabular-nums">
        <time dateTime={run.created_at}>
          {formatDateTime(new Date(run.created_at))}
        </time>
      </dd>
      <dt className="text-ink-secondary">模型</dt>
      <dd className="break-all">{run.model ?? "—"}</dd>
      <dt className="text-ink-secondary">Prompt 版本</dt>
      <dd className="tabular-nums">
        {run.prompt_version === null ? "—" : `v${run.prompt_version}`}
        {run.system_prompt_version !== null &&
          `・系統 prompt v${run.system_prompt_version}`}
      </dd>
    </dl>
  );
}
