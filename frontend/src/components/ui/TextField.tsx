import type { InputHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

import { INPUT_CLASS } from "./controlStyles";
import { WarningCircleIcon } from "./icons";

type TextFieldProps = {
  id: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  /** 顯示在標籤後的「（選填）」 */
  isOptional?: boolean;
  hint?: ReactNode;
  error?: string;
  /** 輸入框右側的按鈕（例如顯示／隱藏金鑰） */
  trailing?: ReactNode;
} & Pick<
  InputHTMLAttributes<HTMLInputElement>,
  | "type"
  | "placeholder"
  | "autoComplete"
  | "inputMode"
  | "spellCheck"
  | "maxLength"
>;

type FieldNotesProps = {
  id: string;
  hint?: ReactNode;
  error?: string;
};

/** 欄位下方的錯誤（圖示＋文字）與說明；id 供輸入框的 aria-describedby 關聯。 */
function FieldNotes({ id, hint, error }: FieldNotesProps) {
  return (
    <>
      {error && (
        <p
          id={`${id}-error`}
          className="flex items-start gap-1 text-footnote text-danger"
        >
          <WarningCircleIcon
            aria-hidden="true"
            className="mt-0.5 size-4 shrink-0"
          />
          {error}
        </p>
      )}
      {hint && (
        <p id={`${id}-hint`} className="text-footnote text-ink-secondary">
          {hint}
        </p>
      )}
    </>
  );
}

function describedByIds(id: string, hasHint: boolean, hasError: boolean) {
  const ids = [hasError && `${id}-error`, hasHint && `${id}-hint`];
  return ids.filter(Boolean).join(" ") || undefined;
}

/** 單行輸入欄位：標籤在上、說明與錯誤在下，錯誤以圖示＋文字呈現並以 aria 關聯。 */
export function TextField({
  id,
  label,
  value,
  onChange,
  isOptional = false,
  hint,
  error,
  trailing,
  ...inputProps
}: TextFieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor={id} className="text-footnote font-semibold text-ink">
        {label}
        {isOptional && (
          <span className="font-normal text-ink-secondary">（選填）</span>
        )}
      </label>
      <div className="flex items-center gap-2">
        <input
          id={id}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={describedByIds(id, Boolean(hint), Boolean(error))}
          className={cn(INPUT_CLASS, "min-w-0 flex-1")}
          {...inputProps}
        />
        {trailing}
      </div>
      <FieldNotes id={id} hint={hint} error={error} />
    </div>
  );
}
