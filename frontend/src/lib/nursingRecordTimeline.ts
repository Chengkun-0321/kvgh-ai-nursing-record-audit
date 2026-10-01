import type {
  AdmissionAssessment,
  Consultation,
  DailyPhysicalAssessment,
  LabResult,
  MedicationAdministration,
  MedicationOrder,
  NursingProgressNote,
  PatientDailyFile,
  Transfer,
  VitalSign,
} from "@/types/dailyPackage";

/** 紀錄類型：護理紀錄頁左側的篩選項目。 */
export type RecordType =
  | "admission_assessment"
  | "daily_physical_assessment"
  | "nursing_progress_note"
  | "transfer"
  | "medication_administration"
  | "consultation"
  | "vital_sign"
  | "lab_result";

export const RECORD_TYPE_OPTIONS: readonly {
  type: RecordType;
  label: string;
}[] = [
  { type: "admission_assessment", label: "入院評估" },
  { type: "daily_physical_assessment", label: "每日身體評估" },
  { type: "nursing_progress_note", label: "護理紀錄" },
  { type: "transfer", label: "轉入轉出" },
  { type: "medication_administration", label: "給藥紀錄" },
  { type: "consultation", label: "會診" },
  { type: "vital_sign", label: "生命徵象" },
  { type: "lab_result", label: "檢驗" },
];

export const ALL_RECORD_TYPES: readonly RecordType[] = RECORD_TYPE_OPTIONS.map(
  ({ type }) => type,
);

export type MedicationOrderInfo = Omit<MedicationOrder, "administrations">;

type TimelineItemBase = {
  /** 跨類型唯一的鍵，用於 React key */
  key: string;
  recordType: RecordType;
  /** 排序與分組依據的時間（ISO 8601，+08:00） */
  occurredAt: string;
};

export type TimelineItem = TimelineItemBase &
  (
    | { kind: "admission_assessment"; record: AdmissionAssessment }
    | { kind: "physical_assessment"; record: DailyPhysicalAssessment }
    | { kind: "progress_note"; record: NursingProgressNote }
    | { kind: "transfer_event"; record: Transfer }
    | {
        kind: "medication";
        order: MedicationOrderInfo;
        administration: MedicationAdministration | null;
      }
    | { kind: "consultation"; record: Consultation }
    | { kind: "vital_sign"; record: VitalSign }
    | { kind: "lab_result"; record: LabResult }
  );

export type TimelineDay = {
  /** 業務日期（YYYY-MM-DD） */
  date: string;
  items: TimelineItem[];
};

// 轉入／轉出摘要是過程紀錄的一種標籤，畫面上歸在「轉入轉出」
const TRANSFER_SUMMARY_CATEGORIES: ReadonlySet<string> = new Set([
  "轉入摘要",
  "轉出摘要",
]);

/**
 * 院方資料為增量：同一筆紀錄修改後會在之後的資料包再出現一次（沿用同一 ID）。
 * 輸入依日期由舊到新，保留最後出現的版本。
 */
function latestById<T>(records: readonly T[], getId: (record: T) => string) {
  const byId = new Map<string, T>();
  for (const record of records) {
    byId.set(getId(record), record);
  }
  return [...byId.values()];
}

function collectAdmissionAssessments(
  files: readonly PatientDailyFile[],
): TimelineItem[] {
  const records = files.flatMap((file) =>
    file.admission_assessment ? [file.admission_assessment] : [],
  );
  return latestById(records, (record) => record.record_id).map((record) => ({
    key: `aas:${record.record_id}`,
    kind: "admission_assessment",
    recordType: "admission_assessment",
    occurredAt: record.assessed_at,
    record,
  }));
}

function collectPhysicalAssessments(
  files: readonly PatientDailyFile[],
): TimelineItem[] {
  const records = files.flatMap((file) => file.daily_physical_assessments);
  return latestById(records, (record) => record.record_id).map((record) => ({
    key: `dpa:${record.record_id}`,
    kind: "physical_assessment",
    recordType: "daily_physical_assessment",
    occurredAt: record.assessed_at,
    record,
  }));
}

function collectProgressNotes(
  files: readonly PatientDailyFile[],
): TimelineItem[] {
  const records = files.flatMap((file) => file.nursing_progress_notes);
  return latestById(records, (record) => record.record_id).map((record) => ({
    key: `npn:${record.record_id}`,
    kind: "progress_note",
    recordType: TRANSFER_SUMMARY_CATEGORIES.has(record.title_category)
      ? "transfer"
      : "nursing_progress_note",
    occurredAt: record.recorded_at,
    record,
  }));
}

function collectTransfers(files: readonly PatientDailyFile[]): TimelineItem[] {
  const records = files.flatMap((file) => file.transfers);
  return latestById(records, (record) => record.transfer_id).map((record) => ({
    key: `trf:${record.transfer_id}`,
    kind: "transfer_event",
    recordType: "transfer",
    occurredAt: record.occurred_at,
    record,
  }));
}

/** 同一張藥囑跨日出現時，以最新版本為準，並合併各天的給藥紀錄。 */
export function mergeMedicationOrders(
  orders: readonly MedicationOrder[],
): MedicationOrder[] {
  const merged = new Map<string, MedicationOrder>();
  for (const order of orders) {
    const previous = merged.get(order.order_id)?.administrations ?? [];
    const administrations = latestById(
      [...previous, ...order.administrations],
      (administration) => administration.administration_id,
    );
    merged.set(order.order_id, { ...order, administrations });
  }
  return [...merged.values()];
}

function toMedicationItems(order: MedicationOrder): TimelineItem[] {
  const { administrations, ...info } = order;
  const base = {
    kind: "medication",
    recordType: "medication_administration",
    order: info,
  } as const;
  if (administrations.length === 0) {
    const key = `med:${order.order_id}`;
    return [
      { ...base, key, occurredAt: order.ordered_at, administration: null },
    ];
  }
  return administrations.map((administration) => ({
    ...base,
    key: `mar:${administration.administration_id}`,
    occurredAt: administration.administered_at,
    administration,
  }));
}

function collectMedications(files: readonly PatientDailyFile[]) {
  const orders = files.flatMap((file) => file.medication_orders);
  return mergeMedicationOrders(orders).flatMap(toMedicationItems);
}

function collectConsultations(
  files: readonly PatientDailyFile[],
): TimelineItem[] {
  const records = files.flatMap((file) => file.consultations);
  const latest = latestById(records, (record) => record.consultation_id);
  return latest.map((record) => ({
    key: `con:${record.consultation_id}`,
    kind: "consultation",
    recordType: "consultation",
    // 會診放在最近一次狀態變化的時間：回覆 → 簽收 → 開立
    occurredAt: record.replied_at ?? record.signed_at ?? record.ordered_at,
    record,
  }));
}

function collectVitalSigns(files: readonly PatientDailyFile[]): TimelineItem[] {
  const records = files.flatMap((file) => file.vital_signs);
  return latestById(records, (record) => record.record_id).map((record) => ({
    key: `vs:${record.record_id}`,
    kind: "vital_sign",
    recordType: "vital_sign",
    occurredAt: record.measured_at,
    record,
  }));
}

function collectLabResults(files: readonly PatientDailyFile[]): TimelineItem[] {
  const records = files.flatMap((file) => file.lab_results);
  return latestById(records, (record) => record.record_id).map((record) => ({
    key: `lab:${record.record_id}`,
    kind: "lab_result",
    recordType: "lab_result",
    occurredAt: record.reported_at ?? record.collected_at,
    record,
  }));
}

const COLLECTORS: readonly ((
  files: readonly PatientDailyFile[],
) => TimelineItem[])[] = [
  collectAdmissionAssessments,
  collectPhysicalAssessments,
  collectProgressNotes,
  collectTransfers,
  collectMedications,
  collectConsultations,
  collectVitalSigns,
  collectLabResults,
];

// 院方時間一律帶 +08:00（見資料格式規格），字串比較即為時間先後
function compareNewestFirst(a: TimelineItem, b: TimelineItem): number {
  if (a.occurredAt !== b.occurredAt) {
    return a.occurredAt < b.occurredAt ? 1 : -1;
  }
  return b.key.localeCompare(a.key);
}

/**
 * 把一位病患多天的資料包攤平成時間軸，由新到舊排序。
 *
 * @param files 依業務日期由舊到新排列的每日檔案
 */
export function buildRecordTimeline(
  files: readonly PatientDailyFile[],
): TimelineItem[] {
  return COLLECTORS.flatMap((collect) => collect(files)).sort(
    compareNewestFirst,
  );
}

/** 依日期分組（輸入需已由新到舊排序）。 */
export function groupTimelineByDate(
  items: readonly TimelineItem[],
): TimelineDay[] {
  const days: TimelineDay[] = [];
  for (const item of items) {
    const date = item.occurredAt.slice(0, 10);
    const lastDay = days.at(-1);
    if (lastDay?.date === date) {
      lastDay.items.push(item);
    } else {
      days.push({ date, items: [item] });
    }
  }
  return days;
}

/** 各紀錄類型的筆數（篩選清單旁顯示）。 */
export function countByRecordType(
  items: readonly TimelineItem[],
): Record<RecordType, number> {
  const counts: Record<RecordType, number> = {
    admission_assessment: 0,
    daily_physical_assessment: 0,
    nursing_progress_note: 0,
    transfer: 0,
    medication_administration: 0,
    consultation: 0,
    vital_sign: 0,
    lab_result: 0,
  };
  for (const item of items) {
    counts[item.recordType] += 1;
  }
  return counts;
}

/** 只保留勾選的紀錄類型。 */
export function filterTimeline(
  items: readonly TimelineItem[],
  selectedTypes: ReadonlySet<RecordType>,
): TimelineItem[] {
  return items.filter((item) => selectedTypes.has(item.recordType));
}
