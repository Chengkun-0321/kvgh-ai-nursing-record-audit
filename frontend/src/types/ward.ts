// TODO(待決): 後端 API 完成後，改用 `npm run gen:api` 產生的 api.ts 型別並刪除本檔

/** 稽核判定（暫定四級，分級方式仍待決）。 */
export type Verdict = "PASS" | "WARNING" | "ERROR" | "NEEDS_REVIEW";

export type Sex = "M" | "F";

/** 病床總覽所需的病患摘要；姓名只供畫面顯示，不可寫入 log。 */
export type PatientSummary = {
  patientKey: string;
  name: string;
  sex: Sex;
  ageYears: number;
  /** 入院日期（YYYY-MM-DD） */
  admissionDate: string;
  diagnosis: string;
};

/** 病床總覽所需的單條規則稽核結果摘要；完整 Evidence 於病患頁面呈現。 */
export type AuditFindingSummary = {
  ruleCode: string;
  verdict: Verdict;
  message: string;
  /** 相關護理紀錄的紀錄時間（ISO 8601） */
  recordedAt: string;
};

export type BedStatus = {
  bedCode: string;
  patient: PatientSummary;
  findings: AuditFindingSummary[];
};

export type WardBedBoard = {
  wardCode: string;
  wardName: string;
  /** 稽核歸屬日（YYYY-MM-DD） */
  businessDate: string;
  beds: BedStatus[];
};
