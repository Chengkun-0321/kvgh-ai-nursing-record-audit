import { afterEach, describe, expect, it, vi } from "vitest";

import { DailyAuditList } from "@/components/patient-audit/DailyAuditList";
import { runAudit } from "@/lib/api/patientAudits";

import { DONE_DAY } from "./fixtures";
import {
  buttonIn,
  cardOf,
  cleanup,
  click,
  flush,
  must,
  render,
} from "./render";

const DETAIL = "尚未設定使用中的模型，請至設定頁設定";

function conflictResponse(): Response {
  return new Response(JSON.stringify({ detail: DETAIL }), {
    status: 409,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(async () => {
  await cleanup();
  vi.unstubAllGlobals();
});

describe("DailyAuditList 稽核失敗", () => {
  it("E12：runAudit 失敗 → 該卡以 role=alert 顯示繁中訊息，保留原結果，按鈕恢復可點", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => conflictResponse()),
    );
    const container = await render(
      <DailyAuditList
        patientKey="P001"
        days={[DONE_DAY]}
        runAudit={runAudit}
      />,
    );

    await click(
      must(buttonIn(cardOf(container, "2026-09-04")), "重新稽核按鈕"),
    );
    await flush();

    const card = cardOf(container, "2026-09-04");
    const alert = must(card.querySelector('[role="alert"]'), "錯誤訊息");
    const button = must(buttonIn(card), "重新稽核按鈕");
    expect(alert.textContent).toContain(DETAIL);
    expect(card.textContent).toContain("虛構稽核訊息甲，請確認");
    expect(button.disabled).toBe(false);
    expect(button.textContent).toContain("重新稽核");
  });
});
