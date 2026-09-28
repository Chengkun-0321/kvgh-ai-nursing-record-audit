"use client";

import { CaretRightIcon, CheckCircleIcon } from "@/components/ui/icons";
import { PROVIDER_CHOICES, type ProviderChoice } from "@/lib/llmProviders";
import { cn } from "@/lib/utils";

type WizardProviderStepProps = {
  selected: ProviderChoice | null;
  isEditing: boolean;
  onChoose: (choice: ProviderChoice) => void;
};

/** 第 1 步：選擇服務類型；點選卡片後直接進入下一步。 */
export function WizardProviderStep({
  selected,
  isEditing,
  onChoose,
}: WizardProviderStepProps) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-body text-ink-secondary">
        {isEditing
          ? "更換服務類型後，需重新填寫連線設定並選擇模型。"
          : "選擇要串接的模型服務，下一步再填寫連線資訊。"}
      </p>
      <ul className="flex flex-col gap-2">
        {PROVIDER_CHOICES.map((option) => {
          const isSelected = option.value === selected;
          return (
            <li key={option.value}>
              <button
                type="button"
                onClick={() => onChoose(option.value)}
                aria-pressed={isSelected}
                className={cn(
                  "flex min-h-16 w-full pressable items-center gap-3 rounded-card bg-surface px-4 py-3 text-left shadow-card focus-ring",
                  isSelected && "ring-2 ring-accent-strong/60",
                )}
              >
                <span className="min-w-0 flex-1">
                  <span className="block text-headline text-ink">
                    {option.label}
                  </span>
                  <span className="block text-footnote text-ink-secondary">
                    {option.description}
                  </span>
                </span>
                {isSelected ? (
                  <span className="flex shrink-0 items-center gap-1 text-footnote font-semibold text-accent-strong">
                    <CheckCircleIcon
                      weight="fill"
                      aria-hidden="true"
                      className="size-5"
                    />
                    目前選擇
                  </span>
                ) : (
                  <CaretRightIcon
                    aria-hidden="true"
                    className="size-5 shrink-0 text-ink-secondary"
                  />
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
