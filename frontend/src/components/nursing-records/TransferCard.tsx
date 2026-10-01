import { TRANSFER_DIRECTION_LABELS } from "@/lib/nursingRecordFormat";
import type { Transfer } from "@/types/dailyPackage";

import { TimelineCard } from "./TimelineCard";

type TransferCardProps = {
  transfer: Transfer;
};

/** 轉入／轉出事件：方向、單位與原因。 */
export function TransferCard({ transfer }: TransferCardProps) {
  const direction = TRANSFER_DIRECTION_LABELS[transfer.direction];

  return (
    <TimelineCard
      occurredAt={transfer.occurred_at}
      badge={direction}
      title={`${direction}：${transfer.from_unit} → ${transfer.to_unit}`}
      recordId={transfer.transfer_id}
    >
      {transfer.reason && (
        <p className="text-body break-words">原因：{transfer.reason}</p>
      )}
    </TimelineCard>
  );
}
