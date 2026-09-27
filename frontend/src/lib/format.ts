// 業務日期以 Asia/Taipei 計算（見 glossary「業務日期」），顯示時間一律固定時區
const TIME_ZONE = "Asia/Taipei";

// 只取各欄位數字再自行組字串：Node 與瀏覽器的 ICU 版本不同，
// 直接 format() 的分隔字元可能不一致，造成 SSR hydration 不符
const PARTS_FORMAT = new Intl.DateTimeFormat("en-US", {
  timeZone: TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const PART_KEYS = ["year", "month", "day", "hour", "minute"] as const;

type PartKey = (typeof PART_KEYS)[number];

type DateTimeParts = Record<PartKey, string>;

function isPartKey(type: string): type is PartKey {
  return PART_KEYS.some((key) => key === type);
}

function toParts(date: Date): DateTimeParts {
  const parts: DateTimeParts = {
    year: "",
    month: "",
    day: "",
    hour: "",
    minute: "",
  };
  for (const { type, value } of PARTS_FORMAT.formatToParts(date)) {
    if (isPartKey(type)) {
      parts[type] = value;
    }
  }
  return parts;
}

/** 將 `YYYY-MM-DD` 格式化為「2026/09/26」。 */
export function formatDate(isoDate: string): string {
  const { year, month, day } = toParts(new Date(`${isoDate}T00:00:00+08:00`));
  return `${year}/${month}/${day}`;
}

/** 格式化為「2026/09/26 14:20」。 */
export function formatDateTime(date: Date): string {
  const { year, month, day, hour, minute } = toParts(date);
  return `${year}/${month}/${day} ${hour}:${minute}`;
}

/** 將 ISO 8601 時間格式化為「09/26 14:20」。 */
export function formatShortDateTime(isoDateTime: string): string {
  const { month, day, hour, minute } = toParts(new Date(isoDateTime));
  return `${month}/${day} ${hour}:${minute}`;
}
