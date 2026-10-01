import type {
  LabResult,
  MedicationAdministration,
  PatientStatus,
  Shift,
  VitalSign,
} from "@/types/dailyPackage";

import { EMPTY_VALUE } from "./assessmentFormat";
import type { MedicationOrderInfo } from "./nursingRecordTimeline";

export const PATIENT_STATUS_LABELS: Record<PatientStatus, string> = {
  inpatient: "住院中",
  transferred_out: "已轉出",
  discharged: "已出院",
};

export const SHIFT_LABELS: Record<Shift, string> = {
  day: "白班",
  evening: "小夜",
  night: "大夜",
};

export const TRANSFER_DIRECTION_LABELS = { in: "轉入", out: "轉出" } as const;

function formatTemperature(record: VitalSign): string | null {
  if (record.body_temperature === null) {
    return null;
  }
  const site = record.temperature_site ? `（${record.temperature_site}）` : "";
  return `T ${record.body_temperature}℃${site}`;
}

function formatBloodPressure(record: VitalSign): string | null {
  if (record.sbp === null || record.dbp === null) {
    return null;
  }
  return `BP ${record.sbp}/${record.dbp}`;
}

function formatSpo2(record: VitalSign): string | null {
  if (record.spo2 === null) {
    return null;
  }
  const oxygen = record.oxygen_therapy ? `（${record.oxygen_therapy}）` : "";
  return `SpO₂ ${record.spo2}%${oxygen}`;
}

/** 生命徵象一行文字，例：「T 36.8℃（耳溫）・P 82・R 18・BP 128/76・SpO₂ 97%（room air）」。 */
export function formatVitalSign(record: VitalSign): string {
  return [
    formatTemperature(record),
    record.pulse === null ? null : `P ${record.pulse}`,
    record.respiration === null ? null : `R ${record.respiration}`,
    formatBloodPressure(record),
    formatSpo2(record),
  ]
    .filter(Boolean)
    .join("・");
}

/** 檢驗結果一行文字，例：「K 3.1 mmol/L（L）」。 */
export function formatLabResult(record: LabResult): string {
  const unit = record.unit ? ` ${record.unit}` : "";
  const flag = record.abnormal_flag ? `（${record.abnormal_flag}）` : "";
  return `${record.item} ${record.value}${unit}${flag}`;
}

/** 藥囑劑量與用法，例：「2 mg IVP STAT」。 */
export function formatOrderDosage(order: MedicationOrderInfo): string {
  return `${order.dose} ${order.unit} ${order.route} ${order.frequency}`;
}

/** 單次給藥的劑量與速率，例：「2 mg・速率 4 mL/hr」。 */
export function formatAdministrationDose(
  administration: MedicationAdministration,
): string {
  const dose =
    administration.dose === null
      ? EMPTY_VALUE
      : `${administration.dose} ${administration.unit ?? ""}`.trim();
  return administration.rate ? `${dose}・速率 ${administration.rate}` : dose;
}
