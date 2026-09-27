"use client";

import { useThree } from "@react-three/fiber";
import { animate, useReducedMotion } from "motion/react";
import { useEffect, useMemo, useRef } from "react";
import type { MeshBasicMaterial, Texture } from "three";

import { BED_DIM_TRANSITION, DIMMED_BED_OPACITY } from "@/lib/motion";
import type { FloorPoint } from "@/lib/wardLayout";
import { getSpritePlane, type WardView } from "@/lib/wardProjection";

type BedSpriteProps = {
  anchor: FloorPoint;
  view: WardView;
  texture: Texture;
  isDimmed: boolean;
};

const SPRITE_RENDER_ORDER = 2;

/** 病床去背圖：正對相機的平面，與相機視角校準一致，看起來就像擺在床位上。 */
export function BedSprite({ anchor, view, texture, isDimmed }: BedSpriteProps) {
  const plane = useMemo(() => getSpritePlane(anchor, view), [anchor, view]);
  const { rotation } = view;
  const materialRef = useRef<MeshBasicMaterial>(null);
  const invalidate = useThree((state) => state.invalidate);
  const shouldReduceMotion = useReducedMotion();

  useEffect(() => {
    const material = materialRef.current;
    if (!material) return;
    const target = isDimmed ? DIMMED_BED_OPACITY : 1;
    const controls = animate(material.opacity, target, {
      ...BED_DIM_TRANSITION,
      duration: shouldReduceMotion ? 0 : BED_DIM_TRANSITION.duration,
      onUpdate: (opacity) => {
        material.opacity = opacity;
        invalidate();
      },
    });
    return () => controls.stop();
  }, [isDimmed, shouldReduceMotion, invalidate]);

  return (
    <mesh
      position={plane.center}
      rotation={[rotation.x, rotation.y, rotation.z, rotation.order]}
      renderOrder={SPRITE_RENDER_ORDER}
    >
      <planeGeometry args={[plane.width, plane.height]} />
      <meshBasicMaterial
        ref={materialRef}
        map={texture}
        transparent
        premultipliedAlpha
        depthWrite={false}
        toneMapped={false}
      />
    </mesh>
  );
}
