import { SCENE_FILL } from "./SceneDefs";

/** 三面床頭櫃配合病床透視；抽屜接縫、桌面反光與接地陰影分開繪製。 */
export function BedsideCabinet() {
  return (
    <g>
      <ellipse cx="91" cy="49" rx="10" ry="4" fill={SCENE_FILL.softShadow} />
      <path d="M83 31 L95 32 L95 47 L83 45 Z" fill={SCENE_FILL.woodFront} />
      <path
        d="M95 32 L100 27 L100 43 L95 47 Z"
        className="fill-scene-wood-shade"
      />
      <path d="M82 30 L87 25 L101 26 L96 32 Z" fill={SCENE_FILL.woodTop} />
      <path
        d="M83 35 L95 36 M83 40 L95 41"
        className="stroke-scene-wood-shade"
        strokeWidth="0.3"
      />
      <path
        d="M87 34 L91 34.4 M87 39 L91 39.4 M87 44 L91 44.4"
        className="stroke-scene-metal-dark"
        strokeWidth="0.7"
      />
      <path
        d="M85 28 L94 29"
        className="stroke-scene-wall/40"
        strokeWidth="0.5"
      />
      <rect
        x="88"
        y="24"
        width="3"
        height="3.5"
        rx="0.5"
        className="fill-scene-bag"
      />
      <ellipse
        cx="89.5"
        cy="24"
        rx="1.5"
        ry="0.6"
        className="fill-scene-wall"
      />
    </g>
  );
}
