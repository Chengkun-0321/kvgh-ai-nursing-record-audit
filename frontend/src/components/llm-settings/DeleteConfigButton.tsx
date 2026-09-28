"use client";

import { useId, useState } from "react";

import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { BUTTON_DANGER } from "@/components/ui/controlStyles";
import { TrashIcon } from "@/components/ui/icons";
import { useAsyncAction } from "@/hooks/useAsyncAction";
import { deleteLlmConfig, type LlmConfig } from "@/lib/api/llmConfigs";
import { cn } from "@/lib/utils";

type DeleteConfigButtonProps = {
  config: LlmConfig;
  onDeleted: (config: LlmConfig) => Promise<void>;
};

/**
 * 刪除設定：先以對話框確認；使用中的設定不可刪除，按鈕保留位置並說明原因。
 */
export function DeleteConfigButton({
  config,
  onDeleted,
}: DeleteConfigButtonProps) {
  const remove = useAsyncAction();
  const [isConfirming, setIsConfirming] = useState(false);
  const hintId = useId();
  const isActive = config.is_active;

  async function handleConfirm() {
    const result = await remove.run(() => deleteLlmConfig(config.id));
    if (result.ok) {
      setIsConfirming(false);
      await onDeleted(config);
    }
  }

  return (
    <div className="ml-auto flex flex-col items-end gap-1">
      <button
        type="button"
        onClick={() => setIsConfirming(!isActive)}
        aria-disabled={isActive || undefined}
        aria-describedby={isActive ? hintId : undefined}
        className={cn(
          BUTTON_DANGER,
          "aria-disabled:cursor-not-allowed aria-disabled:opacity-45",
        )}
      >
        <TrashIcon aria-hidden="true" className="size-4.5" />
        刪除設定
      </button>
      {isActive && (
        <p id={hintId} className="text-footnote text-ink-secondary">
          使用中的設定無法刪除
        </p>
      )}
      <ConfirmDialog
        isOpen={isConfirming}
        title={`刪除「${config.name}」？`}
        description="刪除後無法復原；其他已儲存的設定不受影響。"
        confirmLabel="刪除"
        isPending={remove.isPending}
        errorMessage={remove.errorMessage}
        onConfirm={handleConfirm}
        onCancel={() => {
          setIsConfirming(false);
          remove.clearError();
        }}
      />
    </div>
  );
}
