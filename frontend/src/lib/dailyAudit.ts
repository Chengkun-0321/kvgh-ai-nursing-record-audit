import { formatDateTime, formatTime } from "@/lib/format";
import type { AuditDay, NoteSimilarity } from "@/types/patientAudit";

/** 每日卡片的狀態：不可稽核、尚未稽核、已有稽核結果。 */
export type DayCardState = "not_auditable" | "not_run" | "done";

const EVIDENCE_SOURCE_LABELS: Record<string, string> = {
  nursing_progress_note: "護理過程紀錄",
  vital_sign: "生命徵象",
  lab_result: "檢驗",
  tube: "管路",
};

/** 判斷每日卡片的狀態。 */
export function dayCardState(day: AuditDay): DayCardState {
  if (!day.auditable) {
    return "not_auditable";
  }
  return day.latest_finding === null ? "not_run" : "done";
}

/** 依業務日期由新到舊排序；回傳新陣列，不修改輸入。 */
export function sortDaysDesc(days: AuditDay[]): AuditDay[] {
  return [...days].sort((a, b) =>
    b.business_date.localeCompare(a.business_date),
  );
}

/** 將 `YYYY-MM-DD` 格式化為「9/03」（月不補零、日補兩位），直接解析字串、不經 Date。 */
export function formatBusinessDate(isoDate: string): string {
  const [, month, day] = isoDate.split("-");
  if (month === undefined || day === undefined) {
    return isoDate;
  }
  return `${Number(month)}/${day}`;
}

/**
 * 相似度說明，例：「今日 09:30 紀錄（NPN-B-0904-01）與 9/03 紀錄（NPN-B-0903-01）
 * 相似 98.0%（模型估計）」；沒有相似紀錄時說明未見相似紀錄。
 * 時間以 Asia/Taipei 顯示，不受執行環境時區影響。
 */
export function formatSimilarity(note: NoteSimilarity): string {
  const prefix = `今日 ${formatTime(note.recorded_at)} 紀錄（${note.record_id}）`;
  const {
    similar_record_id: similarRecordId,
    similar_business_date: similarDate,
    similarity_percent: percent,
  } = note;
  if (similarRecordId === null || similarDate === null || percent === null) {
    return `${prefix}未見與前日相似的紀錄`;
  }
  const similarDay = formatBusinessDate(similarDate);
  return `${prefix}與 ${similarDay} 紀錄（${similarRecordId}）相似 ${percent.toFixed(1)}%（模型估計）`;
}

/** 卡片按鈕文字；不可稽核時不顯示按鈕（回傳 `null`）。 */
export function auditButtonLabel(
  day: AuditDay,
  running: boolean,
): string | null {
  const state = dayCardState(day);
  if (state === "not_auditable") {
    return null;
  }
  if (running) {
    return "稽核中…";
  }
  return state === "not_run" ? "執行稽核" : "重新稽核";
}

/** 病患稽核頁的路徑（病患代碼經 URL 編碼）。 */
export function patientAuditPath(patientId: string): string {
  return `/patients/${encodeURIComponent(patientId)}`;
}

/** 安全解碼路由參數；解碼失敗時沿用原字串。 */
export function decodePatientKey(rawPatientKey: string): string {
  try {
    return decodeURIComponent(rawPatientKey);
  } catch {
    return rawPatientKey;
  }
}

/** Evidence 來源的顯示名稱；未知來源顯示原值。 */
export function formatEvidenceSource(source: string): string {
  return EVIDENCE_SOURCE_LABELS[source] ?? source;
}

/** 稽核時間，例：「2026/09/26 14:20」。 */
export function formatAuditedAt(isoDateTime: string): string {
  return formatDateTime(new Date(isoDateTime));
}
