import { WarningCircleIcon } from "@/components/ui/icons";
import { formatShortDateTime } from "@/lib/format";
import {
  formatAdministrationDose,
  formatOrderDosage,
} from "@/lib/nursingRecordFormat";
import type { MedicationOrderInfo } from "@/lib/nursingRecordTimeline";
import type { MedicationAdministration } from "@/types/dailyPackage";

import { TimelineCard } from "./TimelineCard";

type MedicationCardProps = {
  order: MedicationOrderInfo;
  /** 該藥囑沒有任何給藥時為 `null`（卡片放在開立時間） */
  administration: MedicationAdministration | null;
};

function HighAlertLabel() {
  return (
    <span className="inline-flex items-center gap-1 text-footnote font-semibold text-danger">
      <WarningCircleIcon weight="fill" aria-hidden="true" className="size-4" />
      高警訊用藥
    </span>
  );
}

function AdministrationDetail({
  administration,
}: {
  administration: MedicationAdministration;
}) {
  return (
    <p className="rounded-xl bg-canvas px-3 py-2 text-body">
      給藥 {formatShortDateTime(administration.administered_at)}・
      {formatAdministrationDose(administration)}・{administration.status}・
      {administration.administered_by}
      {administration.remark && `（${administration.remark}）`}
    </p>
  );
}

/** 給藥紀錄：藥囑內容、高警訊標示，以及這一次的給藥。 */
export function MedicationCard({ order, administration }: MedicationCardProps) {
  return (
    <TimelineCard
      occurredAt={administration?.administered_at ?? order.ordered_at}
      badge={`${order.order_category}藥囑`}
      title={order.drug_name}
      recordId={administration?.administration_id ?? order.order_id}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-body">
        <span>{formatOrderDosage(order)}</span>
        {order.is_high_alert && <HighAlertLabel />}
      </div>
      <p className="text-footnote text-ink-secondary">
        {order.order_id}・開立 {formatShortDateTime(order.ordered_at)}・
        {order.prescriber_id}・藥囑狀態：{order.status}
      </p>
      {administration ? (
        <AdministrationDetail administration={administration} />
      ) : (
        <p className="text-body text-ink-secondary">尚無給藥紀錄</p>
      )}
    </TimelineCard>
  );
}
