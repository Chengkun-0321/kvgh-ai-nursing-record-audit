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
  key: string,
  search: RawDataSearch,
): Promise<RawViewData> {
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
    // 檢視資料只依賴 patientKey，與病人摘要互不相依，平行載入
    const [patient, data] = await Promise.all([
      getRawPatientDetail(patientKey),
      loadViewData(patientKey, search),
    ]);
    return { ok: true, patient, data };
  } catch (error) {
    return { ok: false, message: toErrorMessage(error) };
  }
}
