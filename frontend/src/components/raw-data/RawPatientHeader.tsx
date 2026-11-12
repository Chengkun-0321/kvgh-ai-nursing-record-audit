import { CheckCircleIcon, CircleIcon } from "@/components/ui/icons";
import type { RawPatientDetail } from "@/lib/api/rawData";
import { formatDate, formatShortDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";

type RawPatientHeaderProps = {
  patient: RawPatientDetail;
};

/** 病人摘要：床號、入院時間、資料日期範圍、工作清單（院方只提供有沒有填寫）。 */
export function RawPatientHeader({ patient }: RawPatientHeaderProps) {
  const dates = patient.business_dates;
  const { work_checklist: checklist } = patient;
  return (
    <header className="flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h1 className="text-large-title tabular-nums">{patient.bed_code}</h1>
        <p className="text-body text-ink-secondary tabular-nums">
          入院{" "}
          {patient.admitted_at
            ? formatShortDateTime(patient.admitted_at)
            : (patient.admitted_at_text ?? "—")}
          ・資料日期 {formatDate(dates[0] ?? "")}–
          {formatDate(dates.at(-1) ?? "")}（{dates.length} 天）
        </p>
        {!patient.is_current && (
          <span className="rounded-full bg-fill px-2.5 py-0.5 text-footnote text-ink-secondary">
            已不在最新一天的病人名單
          </span>
        )}
      </div>
      <section aria-label="工作清單" className="flex flex-col gap-1.5">
        <p className="text-footnote font-semibold text-ink-secondary">
          工作清單 {checklist.filled_count}/{checklist.total_count} 已填寫
        </p>
        <ul className="flex flex-wrap gap-1.5">
          {checklist.items.map((item) => (
            <li
              key={item.label}
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-footnote",
                // 原始資料只呈現狀態，不以警示色判斷對錯；未填寫以空心圓與粗體區分
                item.is_filled
                  ? "bg-canvas text-ink-secondary"
                  : "bg-fill-strong font-semibold text-ink",
              )}
            >
              {item.is_filled ? (
                <CheckCircleIcon aria-hidden="true" className="size-4" />
              ) : (
                <CircleIcon aria-hidden="true" className="size-4" />
              )}
              {item.label}：{item.value}
            </li>
          ))}
        </ul>
      </section>
    </header>
  );
}
