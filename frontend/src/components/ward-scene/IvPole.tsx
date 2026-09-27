import { SCENE_FILL } from "./SceneDefs";

/** 點滴架（床位 SVG 的一部分）：位於床左側，點滴袋與輸液管延伸到床上。 */
export function IvPole() {
  return (
    <g>
      <ellipse cx="9" cy="63" rx="5.5" ry="1.8" fill={SCENE_FILL.softShadow} />
      <path
        d="M5 62.4 L13 62.4"
        strokeWidth="0.9"
        strokeLinecap="round"
        className="stroke-scene-metal-dark"
      />
      <rect
        x="8.6"
        y="11"
        width="0.8"
        height="51.4"
        rx="0.4"
        className="fill-scene-metal"
      />
      <rect
        x="5.5"
        y="10.4"
        width="7"
        height="0.7"
        rx="0.35"
        className="fill-scene-metal-dark"
      />
      <rect
        x="6.2"
        y="11.5"
        width="5.6"
        height="8.5"
        rx="1.6"
        strokeWidth="0.3"
        className="fill-scene-bag stroke-scene-metal"
      />
      <rect
        x="6.7"
        y="15.2"
        width="4.6"
        height="4.3"
        rx="1.2"
        className="fill-scene-window-shade"
      />
      <path
        d="M9 20 C 9 32, 20 38, 28 44"
        strokeWidth="0.35"
        className="fill-none stroke-scene-metal"
      />
    </g>
  );
}
