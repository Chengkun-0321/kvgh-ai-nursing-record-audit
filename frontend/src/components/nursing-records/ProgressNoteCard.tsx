import type { NursingProgressNote } from "@/types/dailyPackage";

import { TimelineCard } from "./TimelineCard";

type ProgressNoteCardProps = {
  note: NursingProgressNote;
};

/** 護理過程紀錄（含轉入／轉出摘要）：標籤、標題與內文原文。 */
export function ProgressNoteCard({ note }: ProgressNoteCardProps) {
  return (
    <TimelineCard
      occurredAt={note.recorded_at}
      badge={note.title_category}
      title={note.title}
      recordId={note.record_id}
      authorId={note.author_id}
      lastModifiedAt={note.last_modified_at}
    >
      <p className="text-body break-words whitespace-pre-line">
        {note.content}
      </p>
    </TimelineCard>
  );
}
