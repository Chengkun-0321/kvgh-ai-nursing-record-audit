// @vitest-environment jsdom
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { renderToStaticMarkup } from "react-dom/server";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { useMediaQuery } from "@/hooks/useMediaQuery";
import type { WardBedBoard } from "@/lib/api/wards";
import { NAV_PAGE_ACTIONS_SLOT_ID } from "@/lib/navSlots";
import { WARD_BOARD_VIEW_STORAGE_KEY } from "@/lib/wardBoardView";

import { BedBoard } from "./BedBoard";
import { makeBoard } from "./wardBoardFixtures";

const { router } = vi.hoisted(() => ({ router: { refresh: vi.fn() } }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));
vi.mock("@/hooks/useMediaQuery", () => ({ useMediaQuery: vi.fn(() => true) }));
// 不在 jsdom 建立 GPU 場景；此測試驗證兩個檢視共用的選床與詳情狀態。
vi.mock("./WardRoomView", () => ({
  WardRoomView: ({
    board,
    selectedBedCode,
  }: {
    board: WardBedBoard;
    selectedBedCode?: string;
  }) => (
    <div data-testid="room" data-selected={selectedBedCode}>
      {board.display_name}
    </div>
  ),
}));

let root: Root;
let container: HTMLDivElement;

beforeEach(() => {
  (
    globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }
  ).IS_REACT_ACT_ENVIRONMENT = true;
  localStorage.clear();
  vi.mocked(useMediaQuery).mockReturnValue(true);
  HTMLDialogElement.prototype.showModal = vi.fn(function (
    this: HTMLDialogElement,
  ) {
    this.open = true;
  });
  HTMLDialogElement.prototype.close = vi.fn(function (this: HTMLDialogElement) {
    this.open = false;
  });
  // layout 在頂部導覽預留的插槽；檢視切換以 portal 放進去
  for (const id of Object.values(NAV_PAGE_ACTIONS_SLOT_ID)) {
    const slot = document.createElement("div");
    slot.id = id;
    document.body.append(slot);
  }
  container = document.createElement("div");
  document.body.append(container);
  root = createRoot(container);
});

afterEach(async () => {
  await act(async () => root.unmount());
  container.remove();
  for (const id of Object.values(NAV_PAGE_ACTIONS_SLOT_ID)) {
    document.getElementById(id)?.remove();
  }
  vi.restoreAllMocks();
});

async function click(element: Element | null) {
  expect(element).not.toBeNull();
  await act(async () => {
    element?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

function viewButton(text: string) {
  return (
    Array.from(
      document.querySelectorAll('[aria-label="病房檢視"] button'),
    ).find((button) => button.textContent === text) ?? null
  );
}

it("預設清單，切換 3D 後保留選床，切回後詳情仍開啟，Esc 焦點回原列", async () => {
  await act(async () => root.render(<BedBoard board={makeBoard()} />));
  expect(container.querySelector("table")).not.toBeNull();
  expect(viewButton("清單")?.getAttribute("aria-pressed")).toBe("true");
  // 切換放在桌機頂部導覽的插槽；狀態列只在 3D 病房顯示
  expect(
    document.getElementById(NAV_PAGE_ACTIONS_SLOT_ID.desktop)?.textContent,
  ).toContain("3D 病房");
  expect(container.querySelector(".ward-status")).toBeNull();

  await click(container.querySelector("tbody tr"));
  expect(container.querySelector("aside#bed-detail")).not.toBeNull();
  await click(viewButton("3D 病房"));
  expect(container.querySelector("table")).toBeNull();
  expect(container.querySelector(".ward-status")).not.toBeNull();
  expect(
    container
      .querySelector('[data-testid="room"]')
      ?.getAttribute("data-selected"),
  ).toBe("W98-1");
  expect(localStorage.getItem(WARD_BOARD_VIEW_STORAGE_KEY)).toBe("3d");

  await click(viewButton("清單"));
  const row = container.querySelector<HTMLElement>("tbody tr");
  expect(row?.getAttribute("aria-selected")).toBe("true");
  expect(container.querySelector("aside#bed-detail")).not.toBeNull();
  await act(async () => {
    document.dispatchEvent(
      new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
    );
  });
  expect(document.activeElement).toBe(row);
  expect(row?.getAttribute("aria-selected")).toBe("false");
});

it("手機點選病患列開啟既有模態詳情，不開桌機大卡", async () => {
  vi.mocked(useMediaQuery).mockReturnValue(false);
  await act(async () => root.render(<BedBoard board={makeBoard()} />));
  await click(container.querySelector("tbody tr"));
  expect(container.querySelector("aside#bed-detail")).toBeNull();
  expect(container.querySelector<HTMLDialogElement>("dialog")?.open).toBe(true);
  expect(container.querySelector("dialog")?.textContent).toContain("W98-1");
});

it("伺服器輸出固定清單，儲存的 3D 偏好留到水合後還原", () => {
  localStorage.setItem(WARD_BOARD_VIEW_STORAGE_KEY, "3d");
  const html = renderToStaticMarkup(<BedBoard board={makeBoard()} />);
  expect(html).toContain("<table");
  expect(html).not.toContain('data-testid="room"');
});
