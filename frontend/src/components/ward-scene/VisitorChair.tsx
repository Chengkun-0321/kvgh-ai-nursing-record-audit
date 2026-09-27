import { SCENE_FILL } from "./SceneDefs";

/** 陪病椅以座面、椅背與金屬腳建立斜俯視厚度。 */
export function VisitorChair() {
  return (
    <g>
      <ellipse cx="91" cy="83" rx="10" ry="4" fill={SCENE_FILL.softShadow} />
      <path
        d="M86 67 L83 82 M96 66 L94 81 M86 71 L88 84 M97 72 L98 82"
        className="fill-none stroke-scene-metal-dark"
        strokeWidth="0.9"
      />
      <path
        d="M85 63 Q82 55 85 53 L95 52 Q98 53 97 61 L95 69 Z"
        className="fill-scene-fabric stroke-scene-metal-dark/60"
        strokeWidth="0.5"
      />
      <path
        d="M85 62 L96 61 L99 70 Q96 75 84 73 L82 70 Z"
        className="fill-scene-fabric"
      />
      <path
        d="M84 64 L95 63 L97 68 Q93 70 84 69 Z"
        className="fill-scene-wall/20"
      />
      <path
        d="M82 64 L80 70 L82 77 M99 62 L101 69 L99 76"
        className="fill-none stroke-scene-metal"
        strokeWidth="0.9"
      />
    </g>
  );
}
