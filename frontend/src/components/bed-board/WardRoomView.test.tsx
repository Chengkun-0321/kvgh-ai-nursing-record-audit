import { renderToStaticMarkup } from "react-dom/server";
import { expect, it, vi } from "vitest";

import { useWardSceneMode } from "@/hooks/useWebGLSupport";

import { makeBoard } from "./wardBoardFixtures";
import { WardRoomView } from "./WardRoomView";

vi.mock("@/hooks/useWebGLSupport", () => ({ useWardSceneMode: vi.fn() }));
vi.mock("@/components/ward-scene/WardMap", () => ({
  WardMap: ({ isSceneEnabled }: { isSceneEnabled: boolean }) => (
    <div data-scene-enabled={isSceneEnabled}>病房地圖</div>
  ),
}));

it("無 WebGL 或場景失敗時使用既有 2D 病床格，仍可開啟詳情", () => {
  vi.mocked(useWardSceneMode).mockReturnValue({
    mode: "2d",
    reportSceneError: vi.fn(),
  });
  const html = renderToStaticMarkup(
    <WardRoomView
      board={makeBoard()}
      activeFilter="ALL"
      onToggle={() => {}}
      onBackgroundClick={() => {}}
    />,
  );
  expect(html).toContain('data-bed-code="W98-1"');
  expect(html).toContain('id="bed-W98-1"');
  expect(html).not.toContain("病房地圖");
});

it.each(["pending", "3d"] as const)(
  "%s 時保留原有病房地圖的載入行為",
  (mode) => {
    vi.mocked(useWardSceneMode).mockReturnValue({
      mode,
      reportSceneError: vi.fn(),
    });
    const html = renderToStaticMarkup(
      <WardRoomView
        board={makeBoard()}
        activeFilter="ALL"
        onToggle={() => {}}
        onBackgroundClick={() => {}}
      />,
    );
    expect(html).toContain(`data-scene-enabled="${mode === "3d"}"`);
  },
);
