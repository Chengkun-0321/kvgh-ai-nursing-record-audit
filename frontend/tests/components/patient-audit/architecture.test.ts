import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

// vitest 在 frontend/ 執行，process.cwd() 即 frontend 根目錄
const TARGET_DIRS = [
  "src/components/patient-audit",
  "src/app/(workspace)/patients",
];

function collectSourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return collectSourceFiles(fullPath);
    }
    return /\.tsx?$/.test(entry.name) ? [fullPath] : [];
  });
}

describe("前端架構約束", () => {
  it("A13：patient-audit 元件與病患頁不得直接呼叫 fetch(", () => {
    const files = TARGET_DIRS.flatMap((directory) =>
      collectSourceFiles(path.join(process.cwd(), directory)),
    );

    const offenders = files.filter((file) =>
      readFileSync(file, "utf-8").includes("fetch("),
    );

    expect(files.length).toBeGreaterThan(0);
    expect(offenders).toEqual([]);
  });
});
