"use client";

import { useState } from "react";

import { EyeIcon, EyeSlashIcon } from "@/components/ui/icons";
import { TextField } from "@/components/ui/TextField";
import type { FieldRequirement } from "@/lib/llmProviders";

type ApiKeyFieldProps = {
  id: string;
  value: string;
  onChange: (value: string) => void;
  requirement: Exclude<FieldRequirement, "unused">;
  /** 已儲存金鑰的遮罩值（如 `sk-…abcd`）；尚未儲存為 `null` */
  storedHint: string | null;
  isClearing: boolean;
  onClearingChange: (isClearing: boolean) => void;
  example?: string;
  /** 取得金鑰的位置說明，接在欄位說明後 */
  sourceHint?: string;
  error?: string;
};

function describeKeyHint(
  storedHint: string | null,
  isClearing: boolean,
  requirement: ApiKeyFieldProps["requirement"],
): string {
  if (storedHint && isClearing) {
    return "儲存後會移除已儲存的金鑰。";
  }
  if (storedHint) {
    return `已儲存：${storedHint}。留空表示不變更。`;
  }
  if (requirement === "optional") {
    return "伺服器需要驗證金鑰時才填寫。";
  }
  return "金鑰會加密儲存，之後畫面只顯示遮罩值。";
}

/** API 金鑰欄位：預設遮蔽輸入內容，可切換顯示；已儲存的金鑰只顯示遮罩值，不回填明文。 */
export function ApiKeyField({
  id,
  value,
  onChange,
  requirement,
  storedHint,
  isClearing,
  onClearingChange,
  example,
  sourceHint,
  error,
}: ApiKeyFieldProps) {
  const [isRevealed, setIsRevealed] = useState(false);
  const RevealIcon = isRevealed ? EyeSlashIcon : EyeIcon;
  const canClear = storedHint !== null && requirement === "optional";

  return (
    <div className="flex flex-col gap-2">
      <TextField
        id={id}
        label="API 金鑰"
        isOptional={requirement === "optional"}
        type={isRevealed ? "text" : "password"}
        value={value}
        onChange={onChange}
        placeholder={storedHint ? "輸入新的金鑰以取代" : example}
        autoComplete="new-password"
        spellCheck={false}
        error={error}
        hint={[describeKeyHint(storedHint, isClearing, requirement), sourceHint]
          .filter(Boolean)
          .join("")}
        trailing={
          <button
            type="button"
            onClick={() => setIsRevealed((previous) => !previous)}
            aria-label={isRevealed ? "隱藏金鑰" : "顯示金鑰"}
            aria-pressed={isRevealed}
            className="grid size-11 shrink-0 pressable place-items-center rounded-xl text-ink-secondary focus-ring hover:bg-fill"
          >
            <RevealIcon aria-hidden="true" className="size-5" />
          </button>
        }
      />
      {canClear && (
        <label className="flex min-h-11 items-center gap-2 text-body text-ink">
          <input
            type="checkbox"
            checked={isClearing}
            onChange={(event) => onClearingChange(event.target.checked)}
            className="size-4.5 accent-accent-strong focus-ring"
          />
          移除已儲存的金鑰
        </label>
      )}
    </div>
  );
}
