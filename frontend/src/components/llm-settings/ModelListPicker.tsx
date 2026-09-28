"use client";

import { BUTTON_SECONDARY, INPUT_CLASS } from "@/components/ui/controlStyles";
import {
  ArrowClockwiseIcon,
  CaretDownIcon,
  WarningCircleIcon,
} from "@/components/ui/icons";
import type { ModelListState } from "@/hooks/useAvailableModels";
import type { AvailableModel } from "@/lib/api/availableModels";
import type { LlmProvider } from "@/lib/api/llmConfigs";
import { DRAFT_FIELD_INPUT_IDS } from "@/lib/llmConfigForm";
import { getProviderOption } from "@/lib/llmProviders";
import { cn } from "@/lib/utils";

type ModelListPickerProps = {
  provider: LlmProvider;
  state: ModelListState;
  value: string;
  error?: string;
  onSelect: (model: string) => void;
  onReload: () => void;
};

const NOTE_CLASS = "text-body text-ink-secondary";

function optionLabel(model: AvailableModel): string {
  return model.label ? `${model.label}（${model.id}）` : model.id;
}

function describeSource(
  provider: LlmProvider,
  state: Extract<ModelListState, { status: "ready" }>,
): string {
  if (state.detection) {
    const server = getProviderOption(state.detection.provider).label;
    return `偵測到${server}：${state.detection.apiBase}`;
  }
  return provider === "chatgpt"
    ? "以下為此 ChatGPT 帳號可用的模型，與 Codex 的模型選單相同。"
    : "以下為服務目前提供、可用於對話的模型。";
}

function ModelSelect({
  state,
  value,
  error,
  onSelect,
}: Omit<ModelListPickerProps, "onReload"> & {
  state: Extract<ModelListState, { status: "ready" }>;
}) {
  const isListed = state.models.some((model) => model.id === value);
  const errorId = `${DRAFT_FIELD_INPUT_IDS.model}-error`;
  return (
    <div className="flex flex-col gap-1.5">
      <label
        htmlFor={DRAFT_FIELD_INPUT_IDS.model}
        className="text-footnote font-semibold text-ink"
      >
        模型
      </label>
      <div className="relative">
        <select
          id={DRAFT_FIELD_INPUT_IDS.model}
          value={value}
          onChange={(event) => onSelect(event.target.value)}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={error ? errorId : undefined}
          className={cn(INPUT_CLASS, "appearance-none pr-10")}
        >
          <option value="" disabled>
            請選擇模型
          </option>
          {value && !isListed && (
            <option value={value}>{value}（目前設定，清單中找不到）</option>
          )}
          {state.models.map((model) => (
            <option key={model.id} value={model.id}>
              {optionLabel(model)}
            </option>
          ))}
        </select>
        <CaretDownIcon
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 right-3.5 size-4.5 -translate-y-1/2 text-ink-secondary"
        />
      </div>
      {error && (
        <p
          id={errorId}
          className="flex items-start gap-1 text-footnote text-danger"
        >
          <WarningCircleIcon
            aria-hidden="true"
            className="mt-0.5 size-4 shrink-0"
          />
          請從清單選擇模型
        </p>
      )}
    </div>
  );
}

function ReadyList(
  props: ModelListPickerProps & {
    state: Extract<ModelListState, { status: "ready" }>;
  },
) {
  const { provider, state, onReload } = props;
  return (
    <>
      <p className={NOTE_CLASS}>{describeSource(provider, state)}</p>
      {state.models.length === 0 ? (
        <p className="text-body text-ink">
          伺服器上還沒有可用的模型。使用 Ollama 時，可先執行 ollama pull
          llama3.2 下載模型，再按「重新整理」。
        </p>
      ) : (
        <ModelSelect {...props} state={state} />
      )}
      <button
        type="button"
        onClick={onReload}
        className={cn(BUTTON_SECONDARY, "self-start")}
      >
        <ArrowClockwiseIcon aria-hidden="true" className="size-4.5" />
        重新整理
      </button>
    </>
  );
}

/** 從服務查到的模型清單中選擇；清單載入中、無法查詢或失敗時說明原因。 */
export function ModelListPicker(props: ModelListPickerProps) {
  const { state, onReload } = props;
  if (state.status === "ready") {
    return <ReadyList {...props} state={state} />;
  }
  if (state.status === "error") {
    return (
      <>
        <p
          role="alert"
          className="flex items-start gap-1.5 text-body text-danger"
        >
          <WarningCircleIcon
            aria-hidden="true"
            className="mt-0.5 size-5 shrink-0"
          />
          {state.message}
        </p>
        <button
          type="button"
          onClick={onReload}
          className={cn(BUTTON_SECONDARY, "self-start")}
        >
          <ArrowClockwiseIcon aria-hidden="true" className="size-4.5" />
          重試
        </button>
      </>
    );
  }
  const message =
    state.status === "blocked" ? state.reason : "正在取得可用模型…";
  return <p className={NOTE_CLASS}>{message}</p>;
}
