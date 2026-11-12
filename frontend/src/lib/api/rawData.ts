import type { components } from "@/types/api";

import { apiJson } from "./client";

export type RawPatientList = components["schemas"]["RawPatientListRead"];
export type RawPatientDetail = components["schemas"]["RawPatientDetailRead"];
export type PatientTimeline = components["schemas"]["PatientTimelineRead"];
export type TimelineEvent = components["schemas"]["TimelineEventRead"];
export type LabMatrix = components["schemas"]["LabMatrixRead"];
export type LabMatrixValue = components["schemas"]["LabMatrixValueRead"];
export type AbnormalFlag = components["schemas"]["AbnormalFlag"];
export type RawSource = components["schemas"]["RawSourceRead"];

/** 時間範圍（含起訖日，YYYY-MM-DD）與類別；未指定表示不限。 */
export type TimelineQuery = {
  startDate?: string;
  endDate?: string;
  /** 照網址原樣傳給後端；不是有效類別時由後端回報錯誤 */
  categories?: readonly string[];
};

function toSearchParams(query: TimelineQuery): string {
  const params = new URLSearchParams();
  if (query.startDate) params.set("start_date", query.startDate);
  if (query.endDate) params.set("end_date", query.endDate);
  for (const category of query.categories ?? []) {
    params.append("categories", category);
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

const patientPath = (patientKey: string) =>
  `/api/v1/raw-patients/${encodeURIComponent(patientKey)}`;

/** 病房所有日期出現過的病人（依床號排序）。 */
export function listRawPatients(wardCode: string): Promise<RawPatientList> {
  return apiJson<RawPatientList>(
    `/api/v1/wards/${encodeURIComponent(wardCode)}/raw-patients`,
  );
}

/** 病人摘要：床號、入院時間、工作清單、各類紀錄筆數。 */
export function getRawPatientDetail(
  patientKey: string,
): Promise<RawPatientDetail> {
  return apiJson<RawPatientDetail>(patientPath(patientKey));
}

/** 病人所有日期合併後的時間軸（日期由新到舊）。 */
export function getPatientTimeline(
  patientKey: string,
  query: TimelineQuery,
): Promise<PatientTimeline> {
  return apiJson<PatientTimeline>(
    `${patientPath(patientKey)}/timeline${toSearchParams(query)}`,
  );
}

/** 檢驗報告的項目 × 採檢時間矩陣。 */
export function getLabMatrix(
  patientKey: string,
  query: TimelineQuery,
): Promise<LabMatrix> {
  const { startDate, endDate } = query;
  return apiJson<LabMatrix>(
    `${patientPath(patientKey)}/lab-matrix${toSearchParams({ startDate, endDate })}`,
  );
}

/** 病人某日（未指定為最新一天）資料檔的原文。 */
export function getPatientSource(
  patientKey: string,
  businessDate?: string,
): Promise<RawSource> {
  const params = businessDate
    ? `?${new URLSearchParams({ business_date: businessDate })}`
    : "";
  return apiJson<RawSource>(`${patientPath(patientKey)}/source${params}`);
}
