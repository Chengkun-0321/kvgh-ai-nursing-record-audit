import { formatShortDateTime } from "@/lib/format";
import { formatLabResult } from "@/lib/nursingRecordFormat";
import type { LabResult } from "@/types/dailyPackage";

import { TimelineCard } from "./TimelineCard";

type LabResultRowProps = {
  labResult: LabResult;
};

/** 檢驗結果單行顯示：項目、數值、參考範圍與採檢時間。 */
export function LabResultRow({ labResult }: LabResultRowProps) {
  const referenceRange = labResult.reference_range
    ? `參考值 ${labResult.reference_range}・`
    : "";

  return (
    <TimelineCard
      compact
      occurredAt={labResult.reported_at ?? labResult.collected_at}
      badge="檢驗"
      title={
        <>
          {formatLabResult(labResult)}
          <span className="ml-2 text-caption text-ink-secondary">
            {referenceRange}採檢 {formatShortDateTime(labResult.collected_at)}
          </span>
        </>
      }
      recordId={labResult.record_id}
    />
  );
}
