import { CheckCircleIcon, WarningCircleIcon } from "@/components/ui/icons";

export type Notice = { tone: "success" | "error"; message: string };

type SettingsNoticeProps = {
  notice: Notice | null;
};

/** 操作結果（已新增、已刪除、錯誤…）；容器常駐，讓螢幕報讀在內容改變時念出。 */
export function SettingsNotice({ notice }: SettingsNoticeProps) {
  const Icon = notice?.tone === "error" ? WarningCircleIcon : CheckCircleIcon;
  return (
    <p role="status" className="empty:hidden">
      {notice && (
        <span className="flex items-start gap-1.5 rounded-card bg-surface px-4 py-3 text-body text-ink shadow-card">
          <Icon
            weight="fill"
            aria-hidden="true"
            className={
              notice.tone === "error"
                ? "mt-0.5 size-5 shrink-0 text-danger"
                : "mt-0.5 size-5 shrink-0 text-accent-strong"
            }
          />
          {notice.message}
        </span>
      )}
    </p>
  );
}
