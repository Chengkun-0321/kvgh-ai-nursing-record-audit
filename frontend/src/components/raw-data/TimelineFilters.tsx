import Link from "next/link";

import {
  BUTTON_PRIMARY,
  BUTTON_SECONDARY,
  INPUT_CLASS,
} from "@/components/ui/controlStyles";
import type { RawPatientDetail } from "@/lib/api/rawData";
import { formatDate } from "@/lib/format";
import { type RawDataSearch, rawDataHref } from "@/lib/rawDataQuery";

type TimelineFiltersProps = {
  patient: RawPatientDetail;
  search: RawDataSearch;
  /** 檢驗總表只依時間範圍篩選，不顯示類別 */
  showCategories: boolean;
};

/**
 * 時間範圍與類別篩選：一般 GET 表單，送出後由伺服器依網址重新取資料，不需前端狀態。
 * 起訖日不設上下限：院方「檢查」會帶出早於資料檔日期的歷史報告。
 */
export function TimelineFilters({
  patient,
  search,
  showCategories,
}: TimelineFiltersProps) {
  const dates = patient.business_dates;
  return (
    <form
      action="/raw-data"
      className="flex flex-col gap-3 rounded-card bg-canvas p-4"
    >
      <input type="hidden" name="patient" value={patient.patient_key} />
      {search.view !== "timeline" && (
        <input type="hidden" name="view" value={search.view} />
      )}
      <div className="flex flex-wrap items-end gap-3">
        <DateField label="起始日期" name="start" value={search.startDate} />
        <DateField label="結束日期" name="end" value={search.endDate} />
        <p className="pb-3 text-footnote text-ink-secondary tabular-nums">
          資料檔日期 {formatDate(dates[0] ?? "")}–
          {formatDate(dates.at(-1) ?? "")}
          ；檢查報告可能早於此範圍
        </p>
      </div>
      {showCategories && (
        <fieldset className="flex flex-wrap gap-1.5">
          <legend className="mb-1.5 text-footnote font-semibold text-ink-secondary">
            紀錄類別（不勾選為全部）
          </legend>
          {patient.category_counts.map(({ category, label, count }) => (
            <label
              key={category}
              className="inline-flex min-h-11 items-center gap-2 rounded-full bg-surface px-3 text-footnote has-checked:bg-accent-tint has-checked:text-accent-strong"
            >
              <input
                type="checkbox"
                name="categories"
                value={category}
                defaultChecked={search.categories.includes(category)}
                className="size-4 accent-accent-strong"
              />
              {label}
              <span className="text-ink-secondary tabular-nums">{count}</span>
            </label>
          ))}
        </fieldset>
      )}
      <div className="flex gap-2">
        <button type="submit" className={BUTTON_PRIMARY}>
          套用篩選
        </button>
        <Link
          href={rawDataHref(search, {
            startDate: null,
            endDate: null,
            categories: [],
          })}
          className={BUTTON_SECONDARY}
        >
          清除
        </Link>
      </div>
    </form>
  );
}

function DateField(props: {
  label: string;
  name: string;
  value: string | null;
}) {
  return (
    <label className="flex flex-col gap-1.5 text-footnote font-semibold text-ink">
      {props.label}
      <input
        type="date"
        name={props.name}
        defaultValue={props.value ?? ""}
        className={`${INPUT_CLASS} w-44 tabular-nums`}
      />
    </label>
  );
}
