import type { TimelineEvent } from "@/lib/api/rawData";
import { formatTime } from "@/lib/format";

import { LabResultTable } from "./LabResultTable";

type TimelineEventCardProps = {
  event: TimelineEvent;
};

/** 時刻欄：院方只給日期時不顯示時刻；時間無法解析時照抄院方原文。 */
function describeTime(event: TimelineEvent): string {
  if (event.occurred_at === null) return event.time_text || "時間不明";
  return event.is_date_only ? "未註明時刻" : formatTime(event.occurred_at);
}

/** 時間軸上的一筆紀錄：類別、標籤、標題、內文、「項目：結果」欄位與檢驗結果，內容皆為院方原文。 */
export function TimelineEventCard({ event }: TimelineEventCardProps) {
  const hasAbnormal =
    event.abnormal_high_count > 0 || event.abnormal_low_count > 0;
  return (
    <article className="grid gap-x-4 gap-y-2 rounded-card bg-surface p-4 shadow-card sm:grid-cols-[5.5rem_minmax(0,1fr)]">
      <p className="text-footnote font-semibold text-ink-secondary tabular-nums">
        {describeTime(event)}
      </p>
      <div className="flex min-w-0 flex-col gap-2">
        <header className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-accent-tint px-2.5 py-0.5 text-footnote font-semibold text-accent-strong">
            {event.category_label}
          </span>
          {event.tag && (
            <span className="rounded-full bg-fill px-2.5 py-0.5 text-footnote">
              {event.tag}
            </span>
          )}
          {event.title && <h3 className="text-headline">{event.title}</h3>}
          {hasAbnormal && (
            <span className="text-footnote text-ink-secondary tabular-nums">
              偏高 {event.abnormal_high_count}・偏低 {event.abnormal_low_count}
            </span>
          )}
        </header>
        {event.text && (
          <p className="text-body whitespace-pre-wrap">{event.text}</p>
        )}
        {event.fields.length > 0 && (
          <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 text-footnote">
            {event.fields.map((field) => (
              <div key={field.label} className="contents">
                <dt className="text-ink-secondary">{field.label}</dt>
                <dd className="whitespace-pre-wrap">{field.value || "—"}</dd>
              </div>
            ))}
          </dl>
        )}
        {event.lab_results.length > 0 && (
          <details className="group">
            <summary className="min-h-11 cursor-pointer content-center text-footnote font-semibold text-accent-strong focus-ring">
              顯示 {event.lab_results.length} 項結果
            </summary>
            <LabResultTable results={event.lab_results} />
          </details>
        )}
      </div>
    </article>
  );
}
