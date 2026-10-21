import Link from "next/link";

import { WarningCircleIcon } from "@/components/ui/icons";
import { patientAuditPath } from "@/lib/dailyAudit";

type AuditDaysLoadErrorProps = {
  patientKey: string;
};

/** 無法取得每日稽核清單時顯示的訊息與重試方式（不顯示任何卡片）。 */
export function AuditDaysLoadError({ patientKey }: AuditDaysLoadErrorProps) {
  return (
    <div className="flex flex-col items-start gap-3 rounded-card bg-canvas p-6">
      <p role="alert" className="flex items-start gap-2 text-body text-ink">
        <WarningCircleIcon
          aria-hidden="true"
          className="mt-0.5 size-5 shrink-0 text-danger"
        />
        無法載入稽核結果
      </p>
      <p className="text-footnote text-ink-secondary">
        請確認後端服務已啟動後再試一次。
      </p>
      <Link
        href={patientAuditPath(patientKey)}
        className="inline-flex min-h-11 pressable items-center rounded-full bg-accent px-5 text-body font-semibold text-accent-contrast focus-ring"
      >
        重新載入
      </Link>
    </div>
  );
}
