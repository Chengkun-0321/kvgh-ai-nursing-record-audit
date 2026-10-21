import { formatEvidenceSource } from "@/lib/dailyAudit";
import type { Evidence } from "@/types/patientAudit";

type EvidenceListProps = {
  evidence: Evidence[];
};

/** 判定依據：來源、紀錄 ID 與原文片段。 */
export function EvidenceList({ evidence }: EvidenceListProps) {
  if (evidence.length === 0) {
    return null;
  }
  return (
    <section aria-label="判定依據" className="flex flex-col gap-2">
      <h3 className="text-footnote font-semibold text-ink-secondary">
        判定依據
      </h3>
      <ul className="flex flex-col gap-2">
        {evidence.map((item, index) => (
          <li
            key={`${item.record_id}-${index}`}
            className="rounded-card bg-canvas px-4 py-3"
          >
            <p className="text-caption text-ink-secondary">
              {formatEvidenceSource(item.source)}・{item.record_id}
            </p>
            {item.excerpt ? (
              <blockquote className="mt-1 text-body whitespace-pre-wrap">
                {item.excerpt}
              </blockquote>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
