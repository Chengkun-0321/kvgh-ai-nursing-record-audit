import { WarningCircleIcon } from "@/components/ui/icons";
import type { RawPatientDetail } from "@/lib/api/rawData";
import { loadRawPatientView, type RawViewData } from "@/lib/api/rawDataView";
import type { RawDataSearch } from "@/lib/rawDataQuery";

import { LabMatrixTable } from "./LabMatrixTable";
import { PatientTimeline } from "./PatientTimeline";
import { RawDataTabs } from "./RawDataTabs";
import { RawPatientHeader } from "./RawPatientHeader";
import { RawSourceView } from "./RawSourceView";
import { TimelineFilters } from "./TimelineFilters";

type RawPatientContentProps = {
  patientKey: string;
  search: RawDataSearch;
};

function ViewBody(props: {
  data: RawViewData;
  patient: RawPatientDetail;
  search: RawDataSearch;
}) {
  const { data } = props;
  if (data.view === "labs") return <LabMatrixTable matrix={data.matrix} />;
  if (data.view === "source") {
    return (
      <RawSourceView
        source={data.source}
        businessDates={props.patient.business_dates}
        search={props.search}
      />
    );
  }
  return <PatientTimeline timeline={data.timeline} />;
}

/** 右欄：病人摘要、檢視切換、篩選與內容；資料都由後端整理好，這裡只負責排版。 */
export async function RawPatientContent({
  patientKey,
  search,
}: RawPatientContentProps) {
  const result = await loadRawPatientView(patientKey, search);
  if (!result.ok) {
    return (
      <p
        role="alert"
        className="flex items-start gap-2 rounded-panel bg-surface p-5 text-body shadow-card"
      >
        <WarningCircleIcon
          aria-hidden="true"
          className="mt-0.5 size-5 shrink-0 text-danger"
        />
        {result.message}
      </p>
    );
  }
  const { patient, data } = result;
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-4 rounded-panel bg-surface p-5 shadow-card">
        <RawPatientHeader patient={patient} />
        <RawDataTabs search={search} />
        {search.view !== "source" && (
          <TimelineFilters
            patient={patient}
            search={search}
            showCategories={search.view === "timeline"}
          />
        )}
      </div>
      <ViewBody data={data} patient={patient} search={search} />
    </div>
  );
}
