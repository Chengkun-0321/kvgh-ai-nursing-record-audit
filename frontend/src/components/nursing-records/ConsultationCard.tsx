import { EMPTY_VALUE } from "@/lib/assessmentFormat";
import { formatShortDateTime } from "@/lib/format";
import type { Consultation } from "@/types/dailyPackage";

import { LabeledValueGrid } from "./LabeledValueGrid";
import { TimelineCard } from "./TimelineCard";

type ConsultationCardProps = {
  consultation: Consultation;
};

function formatOptionalTime(value: string | null): string {
  return value === null ? EMPTY_VALUE : formatShortDateTime(value);
}

const TEXT_CLASS = "text-body break-words whitespace-pre-line";

/** 會診（醫師、營養師）：開立、簽收、回覆時間與內容，顯示最新狀態。 */
export function ConsultationCard({ consultation }: ConsultationCardProps) {
  const times = [
    {
      key: "ordered",
      label: "開立",
      value: formatShortDateTime(consultation.ordered_at),
    },
    {
      key: "signed",
      label: "簽收",
      value: formatOptionalTime(consultation.signed_at),
    },
    {
      key: "replied",
      label: "回覆",
      value: formatOptionalTime(consultation.replied_at),
    },
  ];

  return (
    <TimelineCard
      occurredAt={
        consultation.replied_at ??
        consultation.signed_at ??
        consultation.ordered_at
      }
      badge={`會診・${consultation.status}`}
      title={`${consultation.department}（${consultation.consultant_role}）`}
      recordId={consultation.consultation_id}
    >
      <LabeledValueGrid values={times} />
      {consultation.condition_summary && (
        <p className={TEXT_CLASS}>
          <span className="text-ink-secondary">病況摘要：</span>
          {consultation.condition_summary}
        </p>
      )}
      {consultation.reply_content && (
        <p className={TEXT_CLASS}>
          <span className="text-ink-secondary">回覆內容：</span>
          {consultation.reply_content}
        </p>
      )}
    </TimelineCard>
  );
}
