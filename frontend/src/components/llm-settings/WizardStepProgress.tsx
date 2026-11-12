import type { WizardStep } from "@/lib/api/llmProviders";
import { cn } from "@/lib/utils";

type WizardStepProgressProps = {
  steps: readonly WizardStep[];
  currentIndex: number;
};

/** 步驟進度條：已完成與目前步驟為深藍，其餘為灰；文字步驟數已在標題上方，這裡只做視覺提示。 */
export function WizardStepProgress({
  steps,
  currentIndex,
}: WizardStepProgressProps) {
  return (
    <ol aria-hidden="true" className="flex gap-1.5 px-5 pt-3 pb-4 sm:px-6">
      {steps.map((step, index) => (
        <li
          key={step.step_id}
          className={cn(
            "h-1 flex-1 rounded-full",
            index <= currentIndex ? "bg-accent" : "bg-fill-strong",
          )}
        />
      ))}
    </ol>
  );
}
