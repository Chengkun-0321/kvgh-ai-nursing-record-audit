import { expect, it } from "vitest";

import { WARD_KITS, type WardKit } from "./wardKit";
import {
  buildWardLayout,
  getWardGrid,
  type ModulePlacement,
} from "./wardLayout";

function bedsOf(count: number) {
  return Array.from({ length: count }, (_, index) => ({
    bedCode: `W-${index + 1}`,
  }));
}

function footprint({ moduleId, origin }: ModulePlacement, kit: WardKit) {
  const { bay, edges } = kit;
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

const KITS = Object.entries(WARD_KITS).map(([id, kit]) => ({ id, kit }));

// 兩個視角的尺寸不同，但欄排規則相同，常見床數的結果也一致
it.each(
  KITS.flatMap(({ id, kit }) =>
    [
      [0, 1, 1],
      [1, 1, 1],
      [6, 3, 2],
      [10, 5, 2],
      [40, 8, 5],
      [100, 13, 8],
    ].map(([bedCount = 0, columns, rows]) => ({
      id,
      kit,
      bedCount,
      columns,
      rows,
    })),
  ),
)(
  "$id：$bedCount 床排成 $columns 欄 × $rows 排",
  ({ kit, bedCount, columns, rows }) => {
    expect(getWardGrid(bedCount, kit)).toEqual({ columns, rows });
  },
);

it.each(KITS)("$id：床位由後排往前、每排由左往右", ({ kit }) => {
  const layout = buildWardLayout(bedsOf(7), kit);
  const order = layout.beds.map((bed) => [bed.row, bed.column]);
  expect(order).toEqual(
    [...order].sort(
      (a, b) => (a[0] ?? 0) - (b[0] ?? 0) || (a[1] ?? 0) - (b[1] ?? 0),
    ),
  );
  expect(layout.beds[0]?.anchor).toEqual({
    x: kit.bay.widthM / 2,
    z: kit.bay.bedCenterM,
  });
});

it.each(
  KITS.flatMap(({ id, kit }) =>
    [1, 10, 40, 100].map((bedCount) => ({ id, kit, bedCount })),
  ),
)("$id：$bedCount 床的模組數量正確且原點對齊地磚", ({ kit, bedCount }) => {
  const layout = buildWardLayout(bedsOf(bedCount), kit);
  const { columns, rows } = layout;
  expect(layout.modules).toHaveLength(columns * rows + rows * 2 + columns + 2);
  const snap = kit.grid.snapM;
  const isAligned = (value: number) =>
    Math.abs(value / snap - Math.round(value / snap)) < 1e-9;
  expect(
    layout.modules.every(
      ({ origin }) => isAligned(origin.x) && isAligned(origin.z),
    ),
  ).toBe(true);
});

it.each(KITS)("$id：模組地面範圍互不重疊", ({ kit }) => {
  const rects = buildWardLayout(bedsOf(40), kit).modules.map((placement) =>
    footprint(placement, kit),
  );
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
