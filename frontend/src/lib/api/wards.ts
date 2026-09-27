import { cache } from "react";

import type { BedStatus, WardBedBoard } from "@/types/ward";

import { MOCK_WARD_BED_BOARDS } from "./mockWardData";

/**
 * 取得指定病房的病床總覽（每床的病患摘要與稽核結果摘要）。
 * 以 `cache` 包裝，同一次請求中外框與頁面重複呼叫只取一次。
 *
 * TODO(待決): 後端完成後改為呼叫 `/api/v1/wards/{ward_code}/beds`，目前回傳虛構資料。
 */
export const getWardBedBoard = cache(
  async (wardCode: string): Promise<WardBedBoard> => {
    const board = MOCK_WARD_BED_BOARDS[wardCode];
    if (!board) {
      throw new Error(`查無病房資料：${wardCode}`);
    }
    return board;
  },
);

/**
 * 依病患匿名鍵找出所在病床；查無時回傳 `undefined`。
 *
 * TODO(待決): 後端完成後改為呼叫病患 API，目前從虛構病床總覽查找。
 */
export async function getPatientBed(
  wardCode: string,
  patientKey: string,
): Promise<BedStatus | undefined> {
  const board = await getWardBedBoard(wardCode);
  return board.beds.find((bed) => bed.patient.patientKey === patientKey);
}
