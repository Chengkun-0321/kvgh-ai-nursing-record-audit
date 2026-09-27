import { SCENE_FILL } from "./SceneDefs";

// 設備帶上的醫療氣體出口位置（床位座標，寬 100）
const OUTLET_X = [21, 25, 75, 79] as const;

// 壁掛監視器上的心電圖折線
const ECG_POINTS = "87.6,9 89.4,9 90.1,6.4 91,11.2 91.8,8.2 92.6,9 96.4,9";

/** 壁掛生理監視器（裝飾），位於床頭牆右上方。 */
function WallMonitor() {
  return (
    <g transform="translate(1 0) rotate(7 91 9)">
      <rect
        x="86"
        y="4"
        width="12"
        height="12"
        rx="1"
        className="fill-scene-metal-dark"
      />
      <rect
        x="86.8"
        y="4.8"
        width="10.4"
        height="10.4"
        rx="0.5"
        className="fill-scene-screen"
      />
      <polyline
        points={ECG_POINTS}
        strokeWidth="0.35"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="fill-none stroke-scene-screen-line"
      />
      <path
        d="M88 12 H92 M88 14 H94"
        className="stroke-scene-screen-line/50"
        strokeWidth="0.35"
      />
      <path
        d="M91 16 V24 H87"
        className="fill-none stroke-scene-metal-dark"
        strokeWidth="0.8"
      />
      <rect
        x="93.6"
        y="5.6"
        width="2.8"
        height="0.9"
        rx="0.3"
        className="fill-scene-screen-line/60"
      />
    </g>
  );
}

/**
 * 床頭牆（床位 SVG 的一部分，座標 100×115）：牆頂飾條、牆面、
 * 設備帶（暖色燈條與氣體出口）、壁掛監視器與踢腳板。
 * 相鄰床位的床頭牆會連成一整排；第一排即為後牆下半部。
 */
export function Headwall() {
  return (
    <g>
      <rect width="100" height="30" fill={SCENE_FILL.wallFace} />
      <rect width="100" height="2.2" className="fill-scene-wall-cap" />
      <rect y="28.8" width="100" height="1.4" className="fill-scene-wall-cap" />
      <rect
        x="15"
        y="6.5"
        width="70"
        height="14"
        rx="1.8"
        fill={SCENE_FILL.panel}
      />
      <rect
        x="15"
        y="19.6"
        width="70"
        height="0.9"
        rx="0.45"
        className="fill-scene-panel-shade"
      />
      <ellipse cx="50" cy="9.2" rx="34" ry="5" fill={SCENE_FILL.lampGlow} />
      <rect
        x="21"
        y="8.6"
        width="58"
        height="1.3"
        rx="0.65"
        className="fill-scene-lamp"
      />
      {OUTLET_X.map((x) => (
        <g key={x}>
          <circle cx={x} cy="15.5" r="1.3" className="fill-scene-metal" />
          <circle cx={x} cy="15.5" r="0.55" className="fill-scene-metal-dark" />
        </g>
      ))}
      <WallMonitor />
    </g>
  );
}
