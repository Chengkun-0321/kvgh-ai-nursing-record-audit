import { formatVitalSign } from "@/lib/nursingRecordFormat";
import type { VitalSign } from "@/types/dailyPackage";

import { TimelineCard } from "./TimelineCard";

type VitalSignRowProps = {
  vitalSign: VitalSign;
};

/** 生命徵象單行顯示。 */
export function VitalSignRow({ vitalSign }: VitalSignRowProps) {
  return (
    <TimelineCard
      compact
      occurredAt={vitalSign.measured_at}
      badge="生命徵象"
      title={formatVitalSign(vitalSign)}
      recordId={vitalSign.record_id}
    />
  );
}
