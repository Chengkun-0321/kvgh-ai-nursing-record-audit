// @vitest-environment jsdom
import { act } from "react";
import { createRoot } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it, vi } from "vitest";

import { WardPatientList } from "./WardPatientList";
import { makeBed, makeBoard } from "./wardBoardFixtures";

it.each([0, 1, 10, 40, 100])(
  "%i 位病患各有一列七格，欄標題採 API 順序及短名",
  (count) => {
    const board = makeBoard(
      Array.from({ length: count }, (_, i) => makeBed(i + 1)),
    );
    const container = document.createElement("div");
    container.innerHTML = renderToStaticMarkup(
      <WardPatientList board={board} onToggle={() => {}} />,
    );
    const headers = container.querySelectorAll("thead th");
    expect(headers).toHaveLength(11);
    board.rules.forEach((rule, i) => {
      expect(headers[i + 3]?.textContent).toBe(rule.short_name);
      expect(headers[i + 3]?.getAttribute("title")).toBe(
        `${rule.rule_code} ${rule.name}`,
      );
    });
    const rows = container.querySelectorAll("tbody tr");
    expect(rows).toHaveLength(Math.max(1, count));
    if (count === 0) expect(rows[0]?.textContent).toContain("目前沒有床位資料");
    else expect(rows[0]?.querySelectorAll("td")).toHaveLength(10);
  },
);

it("點列、Enter 與 Space 都選取同一床；清單不篩選、每列都顯示", async () => {
  (
    globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }
  ).IS_REACT_ACT_ENVIRONMENT = true;
  const container = document.createElement("div");
  document.body.append(container);
  const root = createRoot(container);
  const onToggle = vi.fn();
  const board = makeBoard([makeBed(1), makeBed(2, { status: "WARNING" })]);
  await act(async () =>
    root.render(
      <WardPatientList
        board={board}
        selectedBedCode="W98-1"
        onToggle={onToggle}
      />,
    ),
  );
  const rows = container.querySelectorAll("tbody tr");
  const row = rows[0];
  expect(rows).toHaveLength(2);
  expect(row?.classList.contains("opacity-35")).toBe(false);
  expect(rows[1]?.classList.contains("opacity-35")).toBe(false);
  expect(row?.getAttribute("aria-selected")).toBe("true");
  for (const event of [
    new MouseEvent("click", { bubbles: true }),
    new KeyboardEvent("keydown", { key: "Enter", bubbles: true }),
    new KeyboardEvent("keydown", { key: " ", bubbles: true }),
  ]) {
    await act(async () => {
      row?.dispatchEvent(event);
    });
  }
  expect(onToggle.mock.calls).toEqual([["W98-1"], ["W98-1"], ["W98-1"]]);
  await act(async () => {
    row?.dispatchEvent(
      new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }),
    );
  });
  expect(onToggle).toHaveBeenCalledTimes(3);
  await act(async () => root.unmount());
  container.remove();
});
