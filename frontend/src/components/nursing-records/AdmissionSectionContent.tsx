import {
  describeAssessmentItems,
  describeSectionContent,
} from "@/lib/assessmentFormat";
import type {
  AdmissionSectionKey,
  AdmissionSections,
} from "@/types/dailyPackage";

import { LabeledValueGrid } from "./LabeledValueGrid";

type AdmissionSectionContentProps = {
  sections: AdmissionSections;
  sectionKey: AdmissionSectionKey;
};

const TEXT_CLASS = "text-body break-words whitespace-pre-line";

function EnvironmentContent({
  content,
}: {
  content: NonNullable<AdmissionSections["environment"]["content"]>;
}) {
  return (
    <div className="flex flex-col gap-1 text-body">
      <p>已介紹：{content.introduced_items.join("、") || "無"}</p>
      {content.not_introduced.map(({ item, reason }) => (
        <p key={item}>
          未介紹：{item}（原因：{reason}）
        </p>
      ))}
    </div>
  );
}

function PhysicalAssessmentContent({
  content,
}: {
  content: NonNullable<AdmissionSections["physical_assessment"]["content"]>;
}) {
  return (
    <>
      {content.narrative && <p className={TEXT_CLASS}>{content.narrative}</p>}
      <LabeledValueGrid values={describeAssessmentItems(content.items)} />
    </>
  );
}

/** 入院評估單一區塊的內容；未填寫（`content` 為 null）時不顯示內容。 */
export function AdmissionSectionContent({
  sections,
  sectionKey,
}: AdmissionSectionContentProps) {
  if (sectionKey === "physical_assessment") {
    const { content } = sections.physical_assessment;
    return content ? <PhysicalAssessmentContent content={content} /> : null;
  }
  if (sectionKey === "admission_course") {
    const { content } = sections.admission_course;
    return content ? <p className={TEXT_CLASS}>{content.text}</p> : null;
  }
  if (sectionKey === "environment") {
    const { content } = sections.environment;
    return content ? <EnvironmentContent content={content} /> : null;
  }
  const { content } = sections[sectionKey];
  return content ? (
    <LabeledValueGrid values={describeSectionContent(content)} />
  ) : null;
}
