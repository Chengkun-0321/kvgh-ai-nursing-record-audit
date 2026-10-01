"use client";

import { type ReactNode, useState } from "react";

import {
  ALL_RECORD_TYPES,
  countByRecordType,
  filterTimeline,
  type RecordType,
  type TimelineItem,
} from "@/lib/nursingRecordTimeline";

import { RecordTimeline } from "./RecordTimeline";
import { RecordTypeFilter } from "./RecordTypeFilter";

type NursingRecordsViewProps = {
  /** 病患清單（Server Component，由頁面傳入） */
  patientPicker: ReactNode;
  items: TimelineItem[];
};

/**
 * 護理紀錄頁主體：左欄為病患清單與紀錄類型篩選，右側為時間軸。
 * 篩選只在前端進行，切換病患時保留勾選狀態。
 */
export function NursingRecordsView({
  patientPicker,
  items,
}: NursingRecordsViewProps) {
  const [selectedTypes, setSelectedTypes] = useState<ReadonlySet<RecordType>>(
    () => new Set(ALL_RECORD_TYPES),
  );
  const visibleItems = filterTimeline(items, selectedTypes);

  function toggleType(type: RecordType) {
    setSelectedTypes((previous) => {
      const next = new Set(previous);
      if (!next.delete(type)) {
        next.add(type);
      }
      return next;
    });
  }

  return (
    <div className="flex flex-col gap-4 lg:grid lg:grid-cols-[17rem_minmax(0,1fr)] lg:items-start lg:gap-6">
      {/* 桌機左欄固定在導覽下方；比視窗高時自己捲動（外留 padding，卡片陰影不被裁切） */}
      <aside className="flex flex-col gap-4 lg:sticky lg:top-[calc(var(--spacing-toolbar)+0.5rem)] lg:-m-2 lg:max-h-[calc(100dvh-var(--spacing-toolbar)-1rem)] lg:overflow-y-auto lg:p-2">
        {patientPicker}
        <RecordTypeFilter
          counts={countByRecordType(items)}
          selectedTypes={selectedTypes}
          onToggle={toggleType}
          onSelectAll={() => setSelectedTypes(new Set(ALL_RECORD_TYPES))}
          onClear={() => setSelectedTypes(new Set())}
        />
      </aside>
      <section aria-label="紀錄時間軸" className="flex min-w-0 flex-col gap-3">
        <p aria-live="polite" className="text-footnote text-ink-secondary">
          共 {visibleItems.length} 筆，依時間由新到舊
        </p>
        <RecordTimeline items={visibleItems} />
      </section>
    </div>
  );
}
