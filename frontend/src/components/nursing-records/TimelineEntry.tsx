import type { TimelineItem } from "@/lib/nursingRecordTimeline";

import { AdmissionAssessmentCard } from "./AdmissionAssessmentCard";
import { ConsultationCard } from "./ConsultationCard";
import { LabResultRow } from "./LabResultRow";
import { MedicationCard } from "./MedicationCard";
import { PhysicalAssessmentCard } from "./PhysicalAssessmentCard";
import { ProgressNoteCard } from "./ProgressNoteCard";
import { TransferCard } from "./TransferCard";
import { VitalSignRow } from "./VitalSignRow";

type TimelineEntryProps = {
  item: TimelineItem;
};

/** 依紀錄種類選擇對應的卡片。 */
export function TimelineEntry({ item }: TimelineEntryProps) {
  switch (item.kind) {
    case "admission_assessment":
      return <AdmissionAssessmentCard assessment={item.record} />;
    case "physical_assessment":
      return <PhysicalAssessmentCard assessment={item.record} />;
    case "progress_note":
      return <ProgressNoteCard note={item.record} />;
    case "transfer_event":
      return <TransferCard transfer={item.record} />;
    case "medication":
      return (
        <MedicationCard
          order={item.order}
          administration={item.administration}
        />
      );
    case "consultation":
      return <ConsultationCard consultation={item.record} />;
    case "vital_sign":
      return <VitalSignRow vitalSign={item.record} />;
    default:
      return <LabResultRow labResult={item.record} />;
  }
}
