/** 病患稽核頁的網址參數：`date` 為稽核日期（YYYY-MM-DD），未指定時由後端決定預設日。 */

const BUSINESS_DATE_PATTERN = /^\d{4}-\d{2}-\d{2}$/;

/** 確認是真實存在的日期（例如排除 2026-02-30），只檢查格式與曆法，不檢查該日是否有資料。 */
function isCalendarDate(text: string): boolean {
  const [year = 0, month = 0, day = 0] = text.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return (
    date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
  );
}

/**
 * 解析網址的 `date`。格式不對或不是真實日期時視為未指定（回傳 `null`），
 * 交給後端決定預設日；不在前端查詢該日是否有資料。
 */
export function parseAuditDate(
  value: string | string[] | undefined,
): string | null {
  const text = Array.isArray(value) ? value[0] : value;
  if (!text || !BUSINESS_DATE_PATTERN.test(text) || !isCalendarDate(text)) {
    return null;
  }
  return text;
}

/** 組出病患稽核頁的連結；`date` 無效時不寫進網址。 */
export function patientAuditHref(
  patientKey: string,
  date?: string | null,
): string {
  const path = `/patients/${encodeURIComponent(patientKey)}`;
  const businessDate = parseAuditDate(date ?? undefined);
  return businessDate
    ? `${path}?${new URLSearchParams({ date: businessDate })}`
    : path;
}
