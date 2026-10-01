import {
  RECORD_TYPE_OPTIONS,
  type RecordType,
} from "@/lib/nursingRecordTimeline";

type RecordTypeFilterProps = {
  counts: Record<RecordType, number>;
  selectedTypes: ReadonlySet<RecordType>;
  onToggle: (type: RecordType) => void;
  onSelectAll: () => void;
  onClear: () => void;
};

const TEXT_BUTTON_CLASS =
  "min-h-11 pressable rounded-full px-3 text-footnote font-semibold text-accent-strong focus-ring hover:bg-accent-tint";

/** 紀錄類型篩選：勾選要顯示的類型，旁邊為該病患各類型的筆數。 */
export function RecordTypeFilter({
  counts,
  selectedTypes,
  onToggle,
  onSelectAll,
  onClear,
}: RecordTypeFilterProps) {
  return (
    <section
      aria-labelledby="record-type-filter-heading"
      className="rounded-card bg-surface p-3 shadow-card"
    >
      <div className="flex items-center justify-between gap-2 pl-2">
        <h2 id="record-type-filter-heading" className="text-headline">
          紀錄類型
        </h2>
        <div className="flex">
          <button
            type="button"
            onClick={onSelectAll}
            className={TEXT_BUTTON_CLASS}
          >
            全選
          </button>
          <button type="button" onClick={onClear} className={TEXT_BUTTON_CLASS}>
            清除
          </button>
        </div>
      </div>
      <ul className="mt-1 grid grid-cols-2 gap-x-2 lg:grid-cols-1">
        {RECORD_TYPE_OPTIONS.map(({ type, label }) => (
          <li key={type}>
            <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-xl px-2 hover:bg-fill">
              <input
                type="checkbox"
                checked={selectedTypes.has(type)}
                onChange={() => onToggle(type)}
                className="size-4.5 shrink-0 accent-accent focus-ring"
              />
              <span className="min-w-0 flex-1 text-body">{label}</span>
              <span className="text-footnote text-ink-secondary tabular-nums">
                {counts[type]}
              </span>
            </label>
          </li>
        ))}
      </ul>
    </section>
  );
}
