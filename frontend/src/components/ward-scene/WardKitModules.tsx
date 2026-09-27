"use client";

import { useMemo } from "react";

import { getKitAssetUrl, type KitModuleId, WARD_KIT } from "@/lib/wardKit";
import type { FloorPoint, WardLayout } from "@/lib/wardLayout";

import { KitModuleInstances } from "./KitModuleInstances";

type WardKitModulesProps = {
  layout: WardLayout;
};

function groupOrigins(layout: WardLayout): [KitModuleId, FloorPoint[]][] {
  const groups = new Map<KitModuleId, FloorPoint[]>();
  for (const { moduleId, origin } of layout.modules) {
    groups.set(moduleId, [...(groups.get(moduleId) ?? []), origin]);
  }
  return [...groups];
}

/** 牆、地板、床邊設施等場景模組，以及每床的床下陰影。 */
export function WardKitModules({ layout }: WardKitModulesProps) {
  const groups = useMemo(() => groupOrigins(layout), [layout]);
  const bedAnchors = useMemo(
    () => layout.beds.map((bed) => bed.anchor),
    [layout],
  );

  return (
    <>
      {groups.map(([moduleId, origins]) => (
        <KitModuleInstances
          key={moduleId}
          url={getKitAssetUrl(WARD_KIT.modules[moduleId].file)}
          origins={origins}
        />
      ))}
      {bedAnchors.length > 0 && (
        <KitModuleInstances
          url={getKitAssetUrl(WARD_KIT.decals.bedShadow.file)}
          origins={bedAnchors}
          isDecal
        />
      )}
    </>
  );
}
