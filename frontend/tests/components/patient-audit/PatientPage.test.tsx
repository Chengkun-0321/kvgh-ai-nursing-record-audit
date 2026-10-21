import { afterEach, describe, expect, it, vi } from "vitest";

import PatientPage from "@/app/(workspace)/patients/[patientKey]/page";
import { AuditDaysLoadError } from "@/components/patient-audit/AuditDaysLoadError";
import { getAuditDays } from "@/lib/api/patientAudits";

import { DONE_DAY } from "./fixtures";
import { cleanup, must, render } from "./render";

vi.mock("@/lib/api/patientAudits", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api/patientAudits")>()),
  getAuditDays: vi.fn(),
}));

const params = Promise.resolve({ patientKey: "P001" });

function expectLoadErrorView(container: HTMLElement): void {
  expect(container.textContent).toContain("無法載入稽核結果");
  const retry = must(
    Array.from(container.querySelectorAll("a")).find((link) =>
      (link.getAttribute("href") ?? "").includes("/patients/P001"),
    ),
    "重試連結",
  );
  expect(retry).toBeTruthy();
  expect(container.querySelectorAll("article")).toHaveLength(0);
  const buttons = Array.from(container.querySelectorAll("button"));
  expect(
    buttons.some((button) => (button.textContent ?? "").includes("執行稽核")),
  ).toBe(false);
}

afterEach(async () => {
  await cleanup();
  vi.mocked(getAuditDays).mockReset();
});

describe("病患頁載入稽核結果", () => {
  it("E13：getAuditDays 失敗 → 顯示「無法載入稽核結果」與重試連結，不顯示任何卡片", async () => {
    vi.mocked(getAuditDays).mockRejectedValue(new Error("虛構連線失敗"));

    const ui = await PatientPage({ params });
    const container = await render(ui);

    expectLoadErrorView(container);
  });

  it("E13 對照：getAuditDays 成功 → 有日期卡片", async () => {
    vi.mocked(getAuditDays).mockResolvedValue({
      patient_key: "P001",
      days: [DONE_DAY],
    });

    const ui = await PatientPage({ params });
    const container = await render(ui);

    expect(container.querySelectorAll("article").length).toBeGreaterThan(0);
    expect(container.textContent).not.toContain("無法載入稽核結果");
  });

  it("E13：AuditDaysLoadError 顯示錯誤文字與指向病患頁的重試連結", async () => {
    const container = await render(<AuditDaysLoadError patientKey="P001" />);

    expectLoadErrorView(container);
  });
});
