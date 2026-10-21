import { afterEach, describe, expect, it } from "vitest";

import { PatientAuditLink } from "@/components/nursing-records/PatientAuditLink";

import { cleanup, must, render } from "./render";

afterEach(async () => {
  await cleanup();
});

describe("PatientAuditLink", () => {
  it("BR14：顯示「查看稽核結果」連結，指向經 URL 編碼的 /patients/{patient_id}", async () => {
    const container = await render(<PatientAuditLink patientId="A病患" />);

    const link = must(container.querySelector("a"), "查看稽核結果連結");

    expect(link.textContent).toContain("查看稽核結果");
    expect(
      link
        .getAttribute("href")
        ?.endsWith(`/patients/${encodeURIComponent("A病患")}`),
    ).toBe(true);
  });
});
