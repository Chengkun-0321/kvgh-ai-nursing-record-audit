"use client";

import { useLoader, useThree } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef } from "react";
import { type InstancedMesh, Matrix4 } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

import { toUnlitMesh } from "@/lib/sceneAssets";
import type { FloorPoint } from "@/lib/wardLayout";

type KitModuleInstancesProps = {
  url: string;
  origins: readonly FloorPoint[];
  /** 貼花（床下陰影）需要透明混合，並排在不透明模組之後繪製。 */
  isDecal?: boolean;
};

const DECAL_RENDER_ORDER = 1;

/** 同一種模組只載入一次，以 InstancedMesh 一次畫出所有擺放位置。 */
export function KitModuleInstances({
  url,
  origins,
  isDecal = false,
}: KitModuleInstancesProps) {
  const gltf = useLoader(GLTFLoader, url);
  const invalidate = useThree((state) => state.invalidate);
  const meshRef = useRef<InstancedMesh>(null);
  // 材質是自建的 GPU 資源，保留明確的 useMemo 確保 identity，並在更換或卸載時釋放；幾何沿用 GLTF 快取，不釋放
  const { geometry, material } = useMemo(
    () =>
      toUnlitMesh(
        gltf.scene,
        isDecal ? { transparent: true, depthWrite: false } : {},
      ),
    [gltf, isDecal],
  );
  useEffect(() => () => material.dispose(), [material]);

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) return;
    const matrix = new Matrix4();
    origins.forEach((origin, index) => {
      mesh.setMatrixAt(index, matrix.makeTranslation(origin.x, 0, origin.z));
    });
    mesh.instanceMatrix.needsUpdate = true;
    invalidate();
  }, [origins, invalidate]);

  return (
    <instancedMesh
      ref={meshRef}
      args={[geometry, material, origins.length]}
      frustumCulled={false}
      renderOrder={isDecal ? DECAL_RENDER_ORDER : 0}
    />
  );
}
