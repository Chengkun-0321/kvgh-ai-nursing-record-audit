import { CheckCircleIcon, CircleIcon } from "@/components/ui/icons";
import { ADMISSION_SECTIONS } from "@/lib/assessmentFormat";
import type { AdmissionAssessment } from "@/types/dailyPackage";

import { AdmissionSectionContent } from "./AdmissionSectionContent";
import { TimelineCard } from "./TimelineCard";

type AdmissionAssessmentCardProps = {
  assessment: AdmissionAssessment;
};

function CompletedLabel({ completed }: { completed: boolean }) {
  return completed ? (
    <span className="inline-flex items-center gap-1 text-footnote text-positive-strong">
      <CheckCircleIcon weight="fill" aria-hidden="true" className="size-4" />
      已完成
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-footnote text-ink-secondary">
      <CircleIcon aria-hidden="true" className="size-4" />
      未完成
    </span>
  );
}

/** 入院護理評估：8 大項各自的完成狀態與內容原文。 */
export function AdmissionAssessmentCard({
  assessment,
}: AdmissionAssessmentCardProps) {
  const { sections } = assessment;

  return (
    <TimelineCard
      occurredAt={assessment.assessed_at}
      badge="入院評估"
      title="入院護理評估"
      recordId={assessment.record_id}
      authorId={assessment.author_id}
      lastModifiedAt={assessment.last_modified_at}
    >
      {ADMISSION_SECTIONS.map(({ key, label }) => (
        <section
          key={key}
          aria-label={label}
          className="flex flex-col gap-2 border-t border-separator pt-3 first:border-t-0 first:pt-0"
        >
          <div className="flex items-center justify-between gap-3">
            <h4 className="text-headline">{label}</h4>
            <CompletedLabel completed={sections[key].completed} />
          </div>
          <AdmissionSectionContent sections={sections} sectionKey={key} />
        </section>
      ))}
    </TimelineCard>
  );
}
