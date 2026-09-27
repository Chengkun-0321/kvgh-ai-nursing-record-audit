"use client";

import { useLoader } from "@react-three/fiber";
import { useLayoutEffect } from "react";
import { TextureLoader } from "three";

import { getBedSpriteSources } from "@/lib/bedSprites";
import { prepareSpriteTexture } from "@/lib/sceneAssets";
import { isBedDimmed, type VerdictFilterValue } from "@/lib/verdict";
import type { BedSlot } from "@/lib/wardLayout";
import type { WardView } from "@/lib/wardProjection";
import type { BedStatus } from "@/types/ward";

import { BedSprite } from "./BedSprite";

type BedSpriteLayerProps = {
  beds: readonly BedStatus[];
  slots: readonly BedSlot[];
  view: WardView;
  activeFilter: VerdictFilterValue;
};

/** 所有病床去背圖（依視角使用對應素材）；相同圖片只載入一次。 */
export function BedSpriteLayer({
  beds,
  slots,
  view,
  activeFilter,
}: BedSpriteLayerProps) {
  const { sources, uniqueSources } = getBedSpriteSources(beds, view.kit);
  const textures = useLoader(TextureLoader, uniqueSources);

  useLayoutEffect(() => {
    textures.forEach(prepareSpriteTexture);
  }, [textures]);

  return slots.map((slot, index) => {
    const bed = beds[index];
    const texture = textures[uniqueSources.indexOf(sources[index] ?? "")];
    if (!bed || !texture) return null;
    return (
      <BedSprite
        key={slot.bedCode}
        anchor={slot.anchor}
        view={view}
        texture={texture}
        isDimmed={isBedDimmed(bed, activeFilter)}
      />
    );
  });
}
