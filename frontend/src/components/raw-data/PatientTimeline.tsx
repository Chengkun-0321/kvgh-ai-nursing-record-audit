import type { PatientTimeline as PatientTimelineData } from "@/lib/api/rawData";
import { formatDate } from "@/lib/format";

import { TimelineEventCard } from "./TimelineEventCard";

/** 依日分段的時間軸：日期由新到舊，同一天由早到晚（排序由後端決定）。 */
export function PatientTimeline({
  timeline,
}: {
  timeline: PatientTimelineData;
}) {
  if (timeline.days.length === 0) {
    return (
      <p className="rounded-card bg-canvas p-6 text-center text-body text-ink-secondary">
        這段時間內沒有符合條件的紀錄
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-6">
      <p className="text-footnote text-ink-secondary tabular-nums">
        共 {timeline.event_count} 筆紀錄
      </p>
      {timeline.days.map((day) => (
        <section key={day.day} aria-labelledby={`day-${day.day}`}>
          <h2
            id={`day-${day.day}`}
            className="sticky top-0 z-10 mb-2 bg-backdrop/90 py-1 text-headline tabular-nums lg:top-toolbar"
          >
            {formatDate(day.day)}
            <span className="ml-2 text-footnote font-normal text-ink-secondary">
              {day.events.length} 筆
            </span>
          </h2>
          <ol className="flex flex-col gap-2">
            {day.events.map((event) => (
              <li key={event.event_id}>
                <TimelineEventCard event={event} />
              </li>
            ))}
          </ol>
        </section>
      ))}
    </div>
  );
}
