import { useLoader } from "@react-three/fiber";
import {
  type BufferGeometry,
  type Group,
  Mesh,
  MeshBasicMaterial,
  type MeshBasicMaterialParameters,
  SRGBColorSpace,
  Texture,
  TextureLoader,
} from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

import type { BedStatus } from "@/types/ward";

import { getBedSpriteSources } from "./bedSprites";
import { getKitAssetUrl, type WardKit } from "./wardKit";

export type UnlitMesh = {
  geometry: BufferGeometry;
  material: MeshBasicMaterial;
};

function findTexturedMesh(scene: Group): Mesh | undefined {
  let found: Mesh | undefined;
  scene.traverse((node) => {
    if (!found && node instanceof Mesh) found = node;
  });
  return found;
}

function getBaseColorMap(mesh: Mesh): Texture | null {
  const material = Array.isArray(mesh.material)
    ? mesh.material[0]
    : mesh.material;
  if (!material || !("map" in material)) return null;
  return material.map instanceof Texture ? material.map : null;
}

/**
 * 模組 GLB 的貼圖已在 Blender 以固定相機算好光影（投影貼圖），
 * 這裡改用無光照材質直接顯示，網頁上看到的顏色就等於 Blender 算圖結果。
 */
export function toUnlitMesh(
  scene: Group,
  options: MeshBasicMaterialParameters = {},
): UnlitMesh {
  const mesh = findTexturedMesh(scene);
  if (!mesh) throw new Error("場景模組缺少網格");
  const material = new MeshBasicMaterial({
    map: getBaseColorMap(mesh),
    toneMapped: false,
    ...options,
  });
  return { geometry: mesh.geometry, material };
}

/** 病床去背圖貼圖設定：sRGB 色彩，並預乘 alpha，避免光暈邊緣疊在地板上出現暗邊。 */
export function prepareSpriteTexture(texture: Texture): void {
  texture.colorSpace = SRGBColorSpace;
  texture.premultiplyAlpha = true;
  texture.needsUpdate = true;
}

/**
 * 預先下載並解析某個視角的場景模組與病床去背圖，存入 R3F 載入快取；
 * 之後切換到該視角時不必等待，場景不會短暫空白。
 */
export function preloadWardView(kit: WardKit, beds: readonly BedStatus[]) {
  const files = [
    ...Object.values(kit.modules).map((module) => module.file),
    kit.decals.bedShadow.file,
  ];
  for (const file of files) {
    useLoader.preload(GLTFLoader, getKitAssetUrl(kit, file));
  }
  useLoader.preload(
    TextureLoader,
    getBedSpriteSources(beds, kit).uniqueSources,
  );
}
