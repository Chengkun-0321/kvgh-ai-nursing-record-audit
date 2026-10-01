import { describeAssessmentItems } from "@/lib/assessmentFormat";
import { SHIFT_LABELS } from "@/lib/nursingRecordFormat";
import type { DailyPhysicalAssessment } from "@/types/dailyPackage";

import { LabeledValueGrid } from "./LabeledValueGrid";
import { TimelineCard } from "./TimelineCard";

type PhysicalAssessmentCardProps = {
  assessment: DailyPhysicalAssessment;
};

/** 每日身體評估：照院內畫面順序列出全部項目的原值。 */
export function PhysicalAssessmentCard({
  assessment,
}: PhysicalAssessmentCardProps) {
  return (
    <TimelineCard
      occurredAt={assessment.assessed_at}
      badge="每日身體評估"
      title={`${SHIFT_LABELS[assessment.shift]}身體評估`}
      recordId={assessment.record_id}
      authorId={assessment.author_id}
      lastModifiedAt={assessment.last_modified_at}
    >
      <LabeledValueGrid values={describeAssessmentItems(assessment.items)} />
    </TimelineCard>
  );
}
