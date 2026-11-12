/** 原始資料頁的檢視：時間軸、檢驗總表、院方原文。 */
export type RawDataView = "timeline" | "labs" | "source";

/** 原始資料頁的網址狀態；全部放在 query，重新整理或分享連結都能還原畫面。 */
export type RawDataSearch = {
  patient: string | null;
  view: RawDataView;
  startDate: string | null;
  endDate: string | null;
  categories: string[];
  /** 看原文時選擇的資料日期 */
  sourceDate: string | null;
};

export type SearchParamsRecord = Record<string, string | string[] | undefined>;

const VIEWS: readonly RawDataView[] = ["timeline", "labs", "source"];

function first(value: string | string[] | undefined): string | null {
  const text = Array.isArray(value) ? value[0] : value;
  return text ? text : null;
}

function toView(value: string | null): RawDataView {
  return VIEWS.find((view) => view === value) ?? "timeline";
}

/**
 * 讀取網址 query。日期與類別照原樣交給後端檢查，格式錯誤時由後端回報訊息，
 * 不在前端默默改成「不篩選」；檢視名稱屬於頁面路由，無效時回到時間軸。
 */
export function parseRawDataSearch(params: SearchParamsRecord): RawDataSearch {
  const categories = params.categories ?? [];
  return {
    patient: first(params.patient),
    view: toView(first(params.view)),
    startDate: first(params.start),
    endDate: first(params.end),
    categories: Array.isArray(categories) ? categories : [categories],
    sourceDate: first(params.date),
  };
}

/** 組出原始資料頁的連結；`patch` 覆寫部分狀態，預設值（時間軸、未篩選）不寫進網址。 */
export function rawDataHref(
  search: RawDataSearch,
  patch: Partial<RawDataSearch> = {},
): string {
  const next = { ...search, ...patch };
  const entries: [string, string | null][] = [
    ["patient", next.patient],
    ["view", next.view === "timeline" ? null : next.view],
    ["start", next.startDate],
    ["end", next.endDate],
    ...next.categories.map((category): [string, string] => [
      "categories",
      category,
    ]),
    ["date", next.sourceDate],
  ];
  const params = new URLSearchParams(
    entries.filter((entry): entry is [string, string] => entry[1] !== null),
  );
  const query = params.toString();
  return query ? `/raw-data?${query}` : "/raw-data";
}
