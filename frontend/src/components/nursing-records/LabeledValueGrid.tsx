import type { LabeledValue } from "@/lib/assessmentFormat";

type LabeledValueGridProps = {
  values: readonly LabeledValue[];
};

/** 「項目名稱＋值」的格狀清單（身體評估、入院評估各區塊）。 */
export function LabeledValueGrid({ values }: LabeledValueGridProps) {
  return (
    <dl className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
      {values.map(({ key, label, value }) => (
        <div key={key} className="min-w-0 rounded-xl bg-canvas px-3 py-2">
          <dt className="text-caption text-ink-secondary">{label}</dt>
          <dd className="text-body break-words">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
