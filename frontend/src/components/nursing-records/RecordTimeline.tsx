import { formatDate } from "@/lib/format";
import {
  groupTimelineByDate,
  type TimelineItem,
} from "@/lib/nursingRecordTimeline";

import { TimelineEntry } from "./TimelineEntry";

type RecordTimelineProps = {
  items: readonly TimelineItem[];
};

/** 依日期分組的紀錄時間軸（由新到舊）；日期標籤捲動時固定在頂列下方。 */
export function RecordTimeline({ items }: RecordTimelineProps) {
  const days = groupTimelineByDate(items);

  if (days.length === 0) {
    return (
      <p className="rounded-card bg-surface p-8 text-center text-body text-ink-secondary shadow-card">
        沒有符合篩選條件的紀錄
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {days.map((day) => (
        <section
          key={day.date}
          aria-labelledby={`record-day-${day.date}`}
          className="flex flex-col gap-3"
        >
          <h2
            id={`record-day-${day.date}`}
            className="sticky top-[calc(var(--spacing-topbar)+0.5rem)] z-10 self-start lg:top-[calc(var(--spacing-toolbar)+0.5rem)]"
          >
            <span className="glass inline-flex rounded-full px-3 py-1 text-footnote font-semibold tabular-nums shadow-float">
              {formatDate(day.date)}・{day.items.length} 筆
            </span>
          </h2>
          <ol className="flex flex-col gap-3">
            {day.items.map((item) => (
              <li key={item.key}>
                <TimelineEntry item={item} />
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
