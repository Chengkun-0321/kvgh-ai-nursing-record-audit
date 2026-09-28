import { WarningCircleIcon } from "@/components/ui/icons";
import { type ChatEntry, describeChatResult } from "@/lib/chatEntries";
import { cn } from "@/lib/utils";

type ChatMessageBubbleProps = {
  entry: ChatEntry;
};

const BUBBLE_CLASS =
  "rounded-card px-4 py-2.5 text-body break-words whitespace-pre-wrap text-ink";

function describeStatus(entry: ChatEntry): string | null {
  if (entry.result) {
    return describeChatResult(entry.result);
  }
  return entry.status === "stopped" ? "已停止，保留目前收到的內容" : null;
}

/** 一則對話：使用者訊息靠右淺藍底，模型回應靠左灰底；文字一律深色。 */
export function ChatMessageBubble({ entry }: ChatMessageBubbleProps) {
  if (entry.role === "user") {
    return (
      <li className={cn(BUBBLE_CLASS, "max-w-[85%] self-end bg-accent-tint")}>
        <span className="sr-only">你：</span>
        {entry.content}
      </li>
    );
  }

  const status = describeStatus(entry);
  const isWaiting = entry.status === "streaming" && entry.content === "";
  return (
    <li className="flex max-w-[85%] flex-col gap-1.5 self-start">
      {(entry.content || isWaiting) && (
        <p className={cn(BUBBLE_CLASS, "bg-fill")}>
          <span className="sr-only">模型：</span>
          {isWaiting ? (
            <span className="text-ink-secondary">等待回應…</span>
          ) : (
            entry.content
          )}
        </p>
      )}
      {entry.status === "error" && (
        <p className="flex items-start gap-1.5 rounded-card bg-danger-tint px-4 py-2.5 text-body text-danger">
          <WarningCircleIcon
            aria-hidden="true"
            className="mt-0.5 size-5 shrink-0"
          />
          {entry.errorMessage}
        </p>
      )}
      {status && (
        <p className="px-1 text-caption text-ink-secondary">{status}</p>
      )}
    </li>
  );
}
