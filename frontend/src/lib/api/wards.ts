import { cache } from "react";

import type { components } from "@/types/api";

import { apiJson } from "./client";

type WardList = components["schemas"]["WardListRead"];
export type WardBedBoard = components["schemas"]["WardBedBoardRead"];
export type BedStatus = components["schemas"]["BedStatusRead"];
export type BedBoardStatus = components["schemas"]["BedBoardStatus"];
export type StatusCount = components["schemas"]["StatusCountRead"];
export type RuleCell = components["schemas"]["RuleCellRead"];
export type RuleCellState = components["schemas"]["RuleCellState"];
export type PatientSummary = components["schemas"]["PatientSummaryRead"];
export type AuditFindingSummary =
  components["schemas"]["AuditFindingSummaryRead"];

const BASE_PATH = "/api/v1/wards";

/**
 * 有院方資料的病房與預設病房。以 `cache` 包裝，同一次請求中外框與頁面重複呼叫只取一次。
 */
const getWardList = cache((): Promise<WardList> =>
  apiJson<WardList>(BASE_PATH),
);

/** 首頁預設顯示的病房代碼（由後端設定決定）。 */
export async function getDefaultWardCode(): Promise<string> {
  return (await getWardList()).default_ward_code;
}

/**
 * 取得病房的病床總覽；狀態、摘要文字與各狀態床數都由後端算好。
 * 以 `cache` 包裝，同一次請求中外框與頁面重複呼叫只取一次。
 */
export const getWardBedBoard = cache(
  (wardCode: string): Promise<WardBedBoard> =>
    apiJson<WardBedBoard>(
      `${BASE_PATH}/${encodeURIComponent(wardCode)}/bed-board`,
    ),
);
