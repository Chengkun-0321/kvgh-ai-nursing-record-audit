"use client";

import { BUTTON_PRIMARY } from "@/components/ui/controlStyles";
import {
  CaretRightIcon,
  CheckCircleIcon,
  CircleIcon,
  PlusIcon,
} from "@/components/ui/icons";
import type { LlmConfig } from "@/lib/api/llmConfigs";
import { getProviderOption } from "@/lib/llmProviders";
import { cn } from "@/lib/utils";

type LlmConfigListProps = {
  configs: readonly LlmConfig[];
  selectedId: string | null;
  activatingId: string | null;
  onSelect: (configId: string) => void;
  onActivate: (config: LlmConfig) => void;
  onCreate: () => void;
};

type LlmConfigRowProps = {
  config: LlmConfig;
  isSelected: boolean;
  isActivating: boolean;
  onSelect: () => void;
  onActivate: () => void;
};

type ActiveToggleProps = {
  config: LlmConfig;
  isActivating: boolean;
  onActivate: () => void;
};

/** 使用中切換：實心勾選＝使用中，空心圓＝點一下設為使用中。 */
function ActiveToggle({ config, isActivating, onActivate }: ActiveToggleProps) {
  const isActive = config.is_active;
  const Icon = isActive ? CheckCircleIcon : CircleIcon;
  return (
    <button
      type="button"
      onClick={onActivate}
      disabled={isActivating}
      aria-pressed={isActive}
      aria-label={
        isActive ? `「${config.name}」使用中` : `將「${config.name}」設為使用中`
      }
      title={isActive ? "使用中" : "設為使用中"}
      className="grid size-11 shrink-0 pressable place-items-center rounded-full focus-ring hover:bg-fill disabled:opacity-45"
    >
      <Icon
        weight={isActive ? "fill" : "regular"}
        aria-hidden="true"
        className={cn(
          "size-6",
          isActive ? "text-accent-strong" : "text-ink-secondary",
        )}
      />
    </button>
  );
}

function LlmConfigRow({
  config,
  isSelected,
  isActivating,
  onSelect,
  onActivate,
}: LlmConfigRowProps) {
  return (
    <li
      className={cn(
        "flex items-center gap-1 px-1.5",
        isSelected && "bg-accent-tint",
      )}
    >
      <ActiveToggle
        config={config}
        isActivating={isActivating}
        onActivate={onActivate}
      />
      <button
        type="button"
        onClick={onSelect}
        aria-current={isSelected ? "true" : undefined}
        className="flex min-h-16 min-w-0 flex-1 items-center gap-2 rounded-xl py-2 pr-2 pl-1 text-left focus-ring"
      >
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-2">
            <span className="truncate text-body font-semibold text-ink">
              {config.name}
            </span>
            {config.is_active && (
              <span className="shrink-0 rounded-full bg-surface px-2 py-0.5 text-caption font-semibold text-accent-strong ring-1 ring-accent-strong/35">
                使用中
              </span>
            )}
          </span>
          <span className="block truncate text-footnote text-ink-secondary">
            {getProviderOption(config.provider).label}・{config.model}
          </span>
        </span>
        <CaretRightIcon
          aria-hidden="true"
          className="size-4.5 shrink-0 text-ink-secondary"
        />
      </button>
    </li>
  );
}

/**
 * 已儲存的模型設定：左側圓圈切換使用中（同一時間只有一組），點選列本身編輯與測試。
 */
export function LlmConfigList({
  configs,
  selectedId,
  activatingId,
  onSelect,
  onActivate,
  onCreate,
}: LlmConfigListProps) {
  return (
    <section
      aria-labelledby="llm-config-list-heading"
      className="flex flex-col gap-3"
    >
      <div className="flex items-center justify-between gap-2">
        <h2 id="llm-config-list-heading" className="text-headline">
          已儲存的模型
        </h2>
        <button type="button" onClick={onCreate} className={BUTTON_PRIMARY}>
          <PlusIcon aria-hidden="true" className="size-4.5" />
          新增模型
        </button>
      </div>
      {configs.length === 0 ? (
        <p className="rounded-card bg-surface p-5 text-body text-ink-secondary shadow-card">
          尚未儲存任何模型。按「新增模型」逐步完成設定，第一組會自動設為使用中。
        </p>
      ) : (
        <ul className="divide-y divide-separator overflow-hidden rounded-card bg-surface shadow-card">
          {configs.map((config) => (
            <LlmConfigRow
              key={config.id}
              config={config}
              isSelected={config.id === selectedId}
              isActivating={config.id === activatingId}
              onSelect={() => onSelect(config.id)}
              onActivate={() => onActivate(config)}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
