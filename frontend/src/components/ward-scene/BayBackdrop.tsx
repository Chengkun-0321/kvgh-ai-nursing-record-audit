import { BedsideCabinet } from "./BedsideCabinet";
import { Headwall } from "./Headwall";
import { IvPole } from "./IvPole";
import { PrivacyCurtain } from "./PrivacyCurtain";
import { SCENE_FILL } from "./SceneDefs";
import { VisitorChair } from "./VisitorChair";

/**
 * 單一床位的背景（純裝飾）：床頭牆、牆腳陰影、床位燈光、隔簾、床頭櫃、點滴架、陪病椅與床下陰影。
 * 座標系為 100×115，與床位的 `aspect-20/23` 一致，因此等比縮放不變形；
 * 病床素材疊在上方，床頭剛好靠在牆面踢腳板。
 */
export function BayBackdrop() {
  return (
    <svg
      viewBox="0 0 100 115"
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 size-full"
    >
      <Headwall />
      <rect y="30.2" width="100" height="8" fill={SCENE_FILL.wallOcclusion} />
      <ellipse
        cx="50"
        cy="62"
        rx="48"
        ry="40"
        opacity="0.55"
        fill={SCENE_FILL.lampGlow}
      />
      <ellipse cx="50" cy="66" rx="36" ry="32" fill={SCENE_FILL.softShadow} />
      <PrivacyCurtain />
      <BedsideCabinet />
      <VisitorChair />
      <IvPole />
    </svg>
  );
}
