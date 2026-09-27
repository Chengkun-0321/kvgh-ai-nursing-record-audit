import { expect, it } from "vitest";

import {
  clampCamera,
  getInitialCamera,
  getScaleRange,
  getZoomAvailability,
  MAP_LIMITS,
  zoomAt,
} from "./wardMap";

const world = { width: 1600, height: 1000 };
const viewport = { x: 0, y: 0, width: 1200, height: 900 };

it("最小倍率剛好把整個病房放進視窗", () => {
  const range = getScaleRange(viewport, world);
  expect(range.min).toBeCloseTo(0.75);
  expect(range.max).toBe(MAP_LIMITS.maxScale);
});

it("病房很小時上限不低於下限", () => {
  const range = getScaleRange(viewport, { width: 300, height: 200 });
  expect(range.min).toBe(4);
  expect(range.max).toBe(4);
});

it("初始視野以最小倍率置中", () => {
  const camera = getInitialCamera(viewport, world);
  expect(camera.scale).toBeCloseTo(0.75);
  expect(camera.x).toBeCloseTo(0);
  expect(camera.y).toBeCloseTo((900 - 750) / 2);
});

it("窄螢幕的初始視野不低於 50%，置中後由夾限保持在病房內", () => {
  const phone = { x: 0, y: 0, width: 375, height: 700 };
  const camera = getInitialCamera(phone, world);
  expect(camera.scale).toBe(MAP_LIMITS.minInitialScale);
  expect(camera.x).toBeCloseTo((375 - 800) / 2);
});

it("縮放停在最小倍率，無法再縮小", () => {
  const range = getScaleRange(viewport, world);
  const camera = zoomAt(
    getInitialCamera(viewport, world),
    { x: 600, y: 450 },
    0.5,
    range,
  );
  expect(camera.scale).toBeCloseTo(range.min);
  expect(getZoomAvailability(camera.scale, range).canZoomOut).toBe(false);
});

it("放大後病房邊緣不能拖進視窗", () => {
  const range = getScaleRange(viewport, world);
  const camera = clampCamera(
    { x: 200, y: -5000, scale: 1 },
    viewport,
    world,
    range,
  );
  expect(camera.x).toBe(0);
  expect(camera.y).toBe(viewport.height - world.height);
});

it("放不滿的軸置中，並把低於下限的倍率拉回下限", () => {
  const range = getScaleRange(viewport, world);
  const camera = clampCamera(
    { x: 300, y: 300, scale: 0.4 },
    viewport,
    world,
    range,
  );
  expect(camera.scale).toBeCloseTo(0.75);
  expect(camera.x).toBeCloseTo(0);
  expect(camera.y).toBeCloseTo(75);
});

it("安全區有偏移時（側欄、頂列疊在場景上），置中與夾限都相對於安全區", () => {
  const safe = { x: 240, y: 68, width: 1200, height: 900 };
  const range = getScaleRange(safe, world);
  const initial = getInitialCamera(safe, world);
  expect(initial.x).toBeCloseTo(240);
  expect(initial.y).toBeCloseTo(68 + (900 - 750) / 2);
  const zoomed = clampCamera(
    { x: 900, y: -5000, scale: 1 },
    safe,
    world,
    range,
  );
  expect(zoomed.x).toBe(240);
  expect(zoomed.y).toBe(68 + safe.height - world.height);
});
