import type { BedStatus, WardBedBoard } from "@/lib/api/wards";

const RULES = [
  ["R01", "入院經過↔身體評估一致性", "經過↔身評"],
  ["R02", "紀錄複製／一成不變／時效性", "複製／時效"],
  ["R03", "入院護理評估完整性", "入院評估"],
  ["R04", "身評異常追蹤", "異常追蹤"],
  ["R05", "轉入／轉出摘要完整性", "轉出入摘要"],
  ["R06", "會診資訊↔護理紀錄", "會診"],
  ["R07", "給藥後療效與不良反應追蹤", "給藥追蹤"],
] as const;

/** 完全虛構的病床資料；測試不讀取院方資料或實際 API。 */
export function makeBed(index = 1, patch: Partial<BedStatus> = {}): BedStatus {
  return {
    bed_code: `W98-${index}`,
    patient: {
      patient_key: `fictional-${index}`,
      name: null,
      sex: null,
      age_years: null,
      age_group: null,
      admission_date: "2026-01-01",
      length_of_stay_days: 3,
    },
    status: "NOT_AUDITED",
    status_label: "尚未稽核",
    summary_text: "尚未稽核",
    is_pending: false,
    pending_findings: [],
    empty_findings_text: "尚未稽核",
    audited_rule_count: 0,
    auditable_rule_count: 5,
    audit_progress_text: "已稽核 0／5 項",
    rule_cells: RULES.map(([rule_code]) => ({
      rule_code,
      state: "NOT_AUDITED",
      label: "尚未稽核",
      verdict: null,
      finding_count: 0,
    })),
    ...patch,
  };
}

/** 供清單、切換與輪詢測試共用的 W98 病房。 */
export function makeBoard(beds = [makeBed()]): WardBedBoard {
  return {
    ward_code: "W98",
    display_name: "測試病房",
    business_date: "2026-01-04",
    bed_count: beds.length,
    status_counts: [
      { status: "WARNING", label: "需確認", count: 1 },
      { status: "NOT_AUDITED", label: "尚未稽核", count: 1 },
    ],
    beds,
    rules: RULES.map(([rule_code, name, short_name]) => ({
      rule_code,
      name,
      short_name,
    })),
  };
}
