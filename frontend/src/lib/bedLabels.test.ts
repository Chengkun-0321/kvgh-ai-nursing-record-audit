import { describe, expect, it } from "vitest";

import { getBedAriaLabel } from "./bedLabels";

describe("getBedAriaLabel", () => {
  it("依序串接床號、判定摘要與稽核進度", () => {
    expect(
      getBedAriaLabel({
        bed_code: "W63-007",
        summary_text: "需確認 2 項・無法判定 2 項",
        audit_progress_text: "已稽核 4／4 項",
      }),
    ).toBe("W63-007，需確認 2 項・無法判定 2 項，已稽核 4／4 項");
  });

  it("未稽核的病床仍帶上進度文字", () => {
    expect(
      getBedAriaLabel({
        bed_code: "W63-002",
        summary_text: "尚未稽核",
        audit_progress_text: "已稽核 0／3 項",
      }),
    ).toBe("W63-002，尚未稽核，已稽核 0／3 項");
  });
});
