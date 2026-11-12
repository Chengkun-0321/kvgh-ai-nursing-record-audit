import type { RawDataSearch } from "@/lib/rawDataQuery";

import { toErrorMessage } from "./client";
import {
  getLabMatrix,
  getPatientSource,
  getPatientTimeline,
  getRawPatientDetail,
  type LabMatrix,
  type PatientTimeline,
  type RawPatientDetail,
  type RawSource,
} from "./rawData";

/** 右欄目前檢視所需的資料。 */
export type RawViewData =
  | { view: "timeline"; timeline: PatientTimeline }
  | { view: "labs"; matrix: LabMatrix }
  | { view: "source"; source: RawSource };

export type RawPatientViewResult =
  | { ok: true; patient: RawPatientDetail; data: RawViewData }
  | { ok: false; message: string };

async function loadViewData(
  patient: RawPatientDetail,
  search: RawDataSearch,
): Promise<RawViewData> {
  const key = patient.patient_key;
  const query = {
    startDate: search.startDate ?? undefined,
    endDate: search.endDate ?? undefined,
    categories: search.categories,
  };
  if (search.view === "labs") {
    return { view: "labs", matrix: await getLabMatrix(key, query) };
  }
  if (search.view === "source") {
    const date = search.sourceDate ?? undefined;
    return { view: "source", source: await getPatientSource(key, date) };
  }
  return { view: "timeline", timeline: await getPatientTimeline(key, query) };
}

/** 讀取病人摘要與目前檢視的資料；後端回報錯誤（如日期範圍不正確）時回傳可顯示的訊息。 */
export async function loadRawPatientView(
  patientKey: string,
  search: RawDataSearch,
): Promise<RawPatientViewResult> {
  try {
    const patient = await getRawPatientDetail(patientKey);
    return { ok: true, patient, data: await loadViewData(patient, search) };
  } catch (error) {
    return { ok: false, message: toErrorMessage(error) };
  }
}
