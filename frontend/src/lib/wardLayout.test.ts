import { expect, it } from "vitest";

import { WARD_KIT } from "./wardKit";
import {
  buildWardLayout,
  getWardGrid,
  type ModulePlacement,
} from "./wardLayout";

const { bay, edges, grid } = WARD_KIT;

function bedsOf(count: number) {
  return Array.from({ length: count }, (_, index) => ({
    bedCode: `W-${index + 1}`,
  }));
}

function footprint({ moduleId, origin }: ModulePlacement) {
  const isBay = moduleId.startsWith("bay");
  const isFill = moduleId === "frontFill";
  const width = isBay || isFill ? bay.widthM : edges.sideWidthM;
  const depth = moduleId.startsWith("front")
    ? edges.frontDepthM
    : bay.rowPitchM;
  return {
    x0: origin.x,
    z0: origin.z,
    x1: origin.x + width,
    z1: origin.z + depth,
  };
}

it.each([
  [0, 1, 1],
  [1, 1, 1],
  [6, 3, 2],
  [10, 5, 2],
  [40, 8, 5],
  [100, 13, 8],
])("%i 床排成 %i 欄 × %i 排", (bedCount, columns, rows) => {
  expect(getWardGrid(bedCount)).toEqual({ columns, rows });
});

it("床位由後排往前、每排由左往右", () => {
  const layout = buildWardLayout(bedsOf(7));
  const order = layout.beds.map((bed) => [bed.row, bed.column]);
  expect(order).toEqual(
    [...order].sort(
      (a, b) => (a[0] ?? 0) - (b[0] ?? 0) || (a[1] ?? 0) - (b[1] ?? 0),
    ),
  );
  expect(layout.beds[0]?.anchor).toEqual({
    x: bay.widthM / 2,
    z: bay.bedCenterM,
  });
});

it.each([1, 10, 40, 100])("%i 床：模組數量正確且原點對齊地磚", (bedCount) => {
  const layout = buildWardLayout(bedsOf(bedCount));
  const { columns, rows } = layout;
  expect(layout.modules).toHaveLength(columns * rows + rows * 2 + columns + 2);
  const isAligned = (value: number) =>
    Math.abs(value / grid.snapM - Math.round(value / grid.snapM)) < 1e-9;
  expect(
    layout.modules.every(
      ({ origin }) => isAligned(origin.x) && isAligned(origin.z),
    ),
  ).toBe(true);
});

it("模組地面範圍互不重疊", () => {
  const rects = buildWardLayout(bedsOf(40)).modules.map(footprint);
  const overlaps = rects.flatMap((a, i) =>
    rects
      .slice(i + 1)
      .filter(
        (b) =>
          a.x0 < b.x1 - 1e-9 &&
          b.x0 < a.x1 - 1e-9 &&
          a.z0 < b.z1 - 1e-9 &&
          b.z0 < a.z1 - 1e-9,
      ),
  );
  expect(overlaps).toEqual([]);
});
