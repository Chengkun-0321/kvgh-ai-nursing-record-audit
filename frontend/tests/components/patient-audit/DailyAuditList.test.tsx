import { act } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { DailyAuditList } from "@/components/patient-audit/DailyAuditList";
import type { AuditDay, AuditFinding } from "@/types/patientAudit";

import {
  DONE_DAY,
  FIRST_DAY_REASON,
  NOT_AUDITABLE_DAY,
  NOT_RUN_DAY,
  makeFinding,
} from "./fixtures";
import {
  buttonIn,
  cardOf,
  cleanup,
  click,
  deferred,
  flush,
  must,
  render,
} from "./render";

type RunAudit = (
  patientKey: string,
  businessDate: string,
) => Promise<AuditFinding>;

const DAYS: AuditDay[] = [NOT_AUDITABLE_DAY, DONE_DAY, NOT_RUN_DAY];
const SIMILARITY_TEXT =
  "今日 09:30 紀錄（NPN-B-0904-01）與 9/03 紀錄（NPN-B-0903-01）相似 98.0%（模型估計）";

async function renderList(runAudit: RunAudit): Promise<HTMLDivElement> {
  return render(
    <DailyAuditList patientKey="P001" days={DAYS} runAudit={runAudit} />,
  );
}

function unusedRunAudit(): RunAudit {
  return vi.fn<RunAudit>(() => Promise.resolve(makeFinding()));
}

afterEach(async () => {
  await cleanup();
});

describe("DailyAuditList 卡片內容", () => {
  it("BR12：每個日期一張卡，依日期由新到舊排列", async () => {
    const container = await renderList(unusedRunAudit());

    const dates = Array.from(container.querySelectorAll("article")).map(
      (article) => article.getAttribute("data-business-date"),
    );

    expect(dates).toEqual(["2026-09-04", "2026-09-02", "2026-09-01"]);
  });

  it("BR12：卡片標題顯示日期 M/D", async () => {
    const container = await renderList(unusedRunAudit());

    expect(cardOf(container, "2026-09-04").textContent).toContain("9/04");
    expect(cardOf(container, "2026-09-02").textContent).toContain("9/02");
    expect(cardOf(container, "2026-09-01").textContent).toContain("9/01");
  });

  it("BR12：已稽核卡顯示 message、相似度文字、Evidence 與模型名稱", async () => {
    const container = await renderList(unusedRunAudit());

    const text = cardOf(container, "2026-09-04").textContent ?? "";

    expect(text).toContain("虛構稽核訊息甲，請確認");
    expect(text).toContain(SIMILARITY_TEXT);
    expect(text).toContain("NPN-B-0904-01");
    expect(text).toContain("虛構原文片段病人意識清楚");
    expect(text).toContain("fake-model-x");
  });

  it("BR12：未稽核的日期顯示「尚未稽核」", async () => {
    const container = await renderList(unusedRunAudit());

    expect(cardOf(container, "2026-09-02").textContent).toContain("尚未稽核");
  });
});

describe("DailyAuditList 卡片按鈕", () => {
  it("BR13：不可稽核的卡沒有按鈕，顯示 not_auditable_reason", async () => {
    const container = await renderList(unusedRunAudit());

    const card = cardOf(container, "2026-09-01");

    expect(buttonIn(card)).toBeNull();
    expect(card.textContent).toContain(FIRST_DAY_REASON);
  });

  it("BR13：未稽核的卡為「執行稽核」，已稽核的卡為「重新稽核」", async () => {
    const container = await renderList(unusedRunAudit());

    const runButton = must(
      buttonIn(cardOf(container, "2026-09-02")),
      "執行稽核按鈕",
    );
    const rerunButton = must(
      buttonIn(cardOf(container, "2026-09-04")),
      "重新稽核按鈕",
    );

    expect(runButton.textContent).toContain("執行稽核");
    expect(runButton.disabled).toBe(false);
    expect(rerunButton.textContent).toContain("重新稽核");
  });

  it("BR13：請求進行中按鈕停用並顯示「稽核中…」，runAudit 參數正確", async () => {
    const pending = deferred<AuditFinding>();
    const runAudit = vi.fn<RunAudit>(() => pending.promise);
    const container = await renderList(runAudit);

    await click(
      must(buttonIn(cardOf(container, "2026-09-02")), "執行稽核按鈕"),
    );

    const button = must(
      buttonIn(cardOf(container, "2026-09-02")),
      "稽核中按鈕",
    );
    expect(button.disabled).toBe(true);
    expect(button.textContent).toContain("稽核中…");
    expect(runAudit).toHaveBeenCalledTimes(1);
    expect(runAudit).toHaveBeenCalledWith("P001", "2026-09-02");
  });

  it("BR13：成功後該卡以回傳結果更新、按鈕變「重新稽核」，其他卡不變", async () => {
    const pending = deferred<AuditFinding>();
    const container = await renderList(vi.fn<RunAudit>(() => pending.promise));
    const otherBefore = cardOf(container, "2026-09-04").textContent;
    const result = makeFinding({
      id: "00000000-0000-4000-8000-000000000002",
      business_date: "2026-09-02",
      message: "虛構新結果訊息乙，請確認",
    });

    await click(
      must(buttonIn(cardOf(container, "2026-09-02")), "執行稽核按鈕"),
    );
    await act(async () => {
      pending.resolve(result);
      await pending.promise;
    });
    await flush();

    const card = cardOf(container, "2026-09-02");
    const button = must(buttonIn(card), "重新稽核按鈕");
    expect(card.textContent).toContain("虛構新結果訊息乙，請確認");
    expect(card.textContent).not.toContain("尚未稽核");
    expect(button.disabled).toBe(false);
    expect(button.textContent).toContain("重新稽核");
    expect(cardOf(container, "2026-09-04").textContent).toBe(otherBefore);
  });
});
