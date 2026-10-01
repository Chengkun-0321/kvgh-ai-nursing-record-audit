import type { ReactNode } from "react";

import { formatShortDateTime, formatTime } from "@/lib/format";
import { cn } from "@/lib/utils";

type TimelineCardProps = {
  occurredAt: string;
  /** 類型或標籤，例：「健康問題」「生命徵象」 */
  badge: string;
  title: ReactNode;
  recordId: string;
  /** 紀錄者代碼 */
  authorId?: string;
  lastModifiedAt?: string | null;
  /** 單行精簡顯示（生命徵象、檢驗） */
  compact?: boolean;
  children?: ReactNode;
};

/** 時間軸上的一筆紀錄：時間、標籤、標題、紀錄 ID，下方放各類型的內容。 */
export function TimelineCard({
  occurredAt,
  badge,
  title,
  recordId,
  authorId,
  lastModifiedAt,
  compact = false,
  children,
}: TimelineCardProps) {
  return (
    <article
      className={cn(
        "rounded-card bg-surface shadow-card",
        compact ? "px-4 py-2.5" : "p-4",
      )}
    >
      <header className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <time
          dateTime={occurredAt}
          className="text-footnote font-semibold tabular-nums"
        >
          {formatTime(occurredAt)}
        </time>
        <span className="rounded-full bg-fill px-2 py-0.5 text-caption text-ink-secondary">
          {badge}
        </span>
        <h3
          className={cn(
            "min-w-0 flex-1 break-words",
            compact ? "text-body" : "text-headline",
          )}
        >
          {title}
        </h3>
        <span className="text-caption text-ink-secondary tabular-nums">
          {recordId}
        </span>
      </header>
      {children && <div className="mt-3 flex flex-col gap-3">{children}</div>}
      {authorId && (
        <p className="mt-3 text-caption text-ink-secondary">
          紀錄者 {authorId}
          {lastModifiedAt && `・修改於 ${formatShortDateTime(lastModifiedAt)}`}
        </p>
      )}
    </article>
  );
}
