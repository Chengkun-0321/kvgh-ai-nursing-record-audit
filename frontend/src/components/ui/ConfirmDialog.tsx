"use client";

import { useEffect, useId, useRef } from "react";

import { BUTTON_DANGER, BUTTON_SECONDARY } from "./controlStyles";
import { WarningCircleIcon } from "./icons";

type ConfirmDialogProps = {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  isPending: boolean;
  errorMessage: string | null;
  onConfirm: () => void;
  onCancel: () => void;
};

/**
 * 破壞性操作的確認對話框：原生 `<dialog>` 的 `showModal()` 提供 Esc 關閉、背景 inert，
 * 關閉後焦點回到觸發按鈕；預設焦點放在「取消」，避免誤按確認。
 */
export function ConfirmDialog({
  isOpen,
  title,
  description,
  confirmLabel,
  isPending,
  errorMessage,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const descriptionId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (isOpen && dialog && !dialog.open) {
      dialog.showModal();
    }
    if (!isOpen && dialog?.open) {
      dialog.close();
    }
  }, [isOpen]);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
      onCancel={(event) => {
        event.preventDefault();
        onCancel();
      }}
      className="m-auto w-[min(24rem,calc(100vw-2rem))] rounded-panel bg-surface p-6 text-ink shadow-float backdrop:bg-scrim"
    >
      <h2 id={titleId} className="text-headline">
        {title}
      </h2>
      <p id={descriptionId} className="mt-2 text-body text-ink-secondary">
        {description}
      </p>
      {errorMessage && (
        <p
          role="alert"
          className="mt-3 flex items-start gap-1.5 text-footnote text-danger"
        >
          <WarningCircleIcon
            aria-hidden="true"
            className="mt-0.5 size-4 shrink-0"
          />
          {errorMessage}
        </p>
      )}
      <div className="mt-6 flex justify-end gap-2">
        <button
          type="button"
          autoFocus
          onClick={onCancel}
          className={BUTTON_SECONDARY}
        >
          取消
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={isPending}
          className={BUTTON_DANGER}
        >
          {isPending ? "處理中…" : confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
