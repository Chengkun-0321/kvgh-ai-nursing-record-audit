import { SCENE_FILL } from "./SceneDefs";

type NurseStationProps = {
  className?: string;
};

// 護理站桌上的兩台螢幕（左上角 x 座標）
const SCREEN_X = [104, 166] as const;

/** 護理站桌上螢幕（面向護理師座位）。 */
function DeskScreen({ x }: { x: number }) {
  return (
    <g>
      <rect
        x={x + 12}
        y="44"
        width="6"
        height="8"
        className="fill-scene-metal-dark"
      />
      <rect
        x={x}
        y="22"
        width="30"
        height="22"
        rx="2"
        className="fill-scene-metal-dark"
      />
      <rect
        x={x + 1.6}
        y="23.6"
        width="26.8"
        height="17.6"
        rx="1"
        className="fill-scene-screen"
      />
      <rect
        x={x + 4}
        y="27"
        width="14"
        height="1.6"
        rx="0.8"
        className="fill-scene-screen-line/70"
      />
      <rect
        x={x + 4}
        y="31"
        width="21"
        height="1.2"
        rx="0.6"
        className="fill-scene-screen-line/40"
      />
      <rect
        x={x + 4}
        y="34.6"
        width="17"
        height="1.2"
        rx="0.6"
        className="fill-scene-screen-line/40"
      />
    </g>
  );
}

/**
 * 病房下方的護理站（純裝飾）：弧形櫃台、桌面、兩台螢幕、鍵盤與座椅。
 * 座標 300×110，由外層以容器寬度（cqw）決定大小。
 */
export function NurseStation({ className }: NurseStationProps) {
  return (
    <svg viewBox="0 0 300 110" aria-hidden="true" className={className}>
      <ellipse cx="150" cy="84" rx="150" ry="22" fill={SCENE_FILL.softShadow} />
      <path
        d="M20 30 Q150 2 280 30 L280 42 Q150 14 20 42 Z"
        fill={SCENE_FILL.woodTop}
      />
      <path
        d="M20 42 Q150 14 280 42 L280 49 Q150 21 20 49 Z"
        fill={SCENE_FILL.woodFront}
      />
      <path
        d="M12 49 Q150 20 288 49 L288 70 Q150 41 12 70 Z"
        className="fill-scene-wall"
      />
      <path
        d="M12 70 Q150 41 288 70 L288 79 Q150 50 12 79 Z"
        className="fill-scene-wall-shade"
      />
      {SCREEN_X.map((x) => (
        <DeskScreen key={x} x={x} />
      ))}
      <rect
        x="128"
        y="52"
        width="44"
        height="6"
        rx="1.4"
        className="fill-scene-metal"
      />
      <rect
        x="136"
        y="80"
        width="28"
        height="8"
        rx="3"
        className="fill-scene-fabric"
      />
      <ellipse cx="150" cy="96" rx="15" ry="9" className="fill-scene-fabric" />
      <ellipse
        cx="150"
        cy="94"
        rx="10"
        ry="4.5"
        className="fill-scene-wall/20"
      />
    </svg>
  );
}
