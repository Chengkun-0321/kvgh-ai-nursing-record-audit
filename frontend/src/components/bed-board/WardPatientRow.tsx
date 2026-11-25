import type { KeyboardEvent } from "react";

import type { BedStatus } from "@/lib/api/wards";
import { cn } from "@/lib/utils";
import { getBedButtonId } from "@/lib/wardMap";

import { BED_DETAIL_PANEL_ID } from "./BedDetailPanel";
import { RuleCellBadge } from "./RuleCellBadge";

type WardPatientRowProps = {
  bed: BedStatus;
  isSelected: boolean;
  onToggle: (bedCode: string) => void;
};

/** 保留原生表格語意；整列支援滑鼠與 Enter／Space，與床位圖共用詳情及焦點還原。 */
export function WardPatientRow({
  bed,
  isSelected,
  onToggle,
}: WardPatientRowProps) {
  function handleKeyDown(event: KeyboardEvent<HTMLTableRowElement>) {
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault();
    onToggle(bed.bed_code);
  }
  return (
    <tr
      id={getBedButtonId(bed.bed_code)}
      tabIndex={0}
      data-keep-detail
      data-bed-code={bed.bed_code}
      aria-selected={isSelected}
      aria-controls={isSelected ? BED_DETAIL_PANEL_ID : undefined}
      onClick={() => onToggle(bed.bed_code)}
      onKeyDown={handleKeyDown}
      className={cn(
        "group h-11 cursor-pointer focus-ring transition-opacity hover:bg-canvas",
        isSelected && "bg-canvas",
      )}
    >
      <th
        scope="row"
        className={cn(
          "sticky left-0 z-10 bg-surface px-3 py-2 text-left font-semibold tabular-nums group-hover:bg-canvas",
          isSelected && "bg-canvas text-accent-strong",
        )}
      >
        {bed.bed_code}
        {isSelected && <span className="sr-only">（已選取）</span>}
      </th>
      <td className="px-3 py-2 tabular-nums">
        {bed.patient.admission_date ?? "—"}
      </td>
      <td className="px-3 py-2 tabular-nums">
        {bed.patient.length_of_stay_days ?? "—"}
      </td>
      {bed.rule_cells.map((cell) => (
        <td key={cell.rule_code} className="px-3 py-2">
          <RuleCellBadge cell={cell} />
        </td>
      ))}
      <td className="min-w-40 px-3 py-2 whitespace-normal text-ink-secondary">
        {bed.summary_text}
      </td>
    </tr>
  );
}
