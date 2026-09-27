import { SCENE_FILL } from "./SceneDefs";

const FOLDS = [0, 1.2, 2.4, 3.6, 4.8, 6] as const;

/** 隔簾沿走道方向向前延伸，頂軌、褶皺及地面影子共用病床的斜俯視角。 */
export function PrivacyCurtain() {
  return (
    <g>
      <path d="M1 28 L7 24 L17 89 L11 95 Z" fill={SCENE_FILL.softShadow} />
      <path d="M2 2 L8 0 L4 77 L-2 80 Z" fill={SCENE_FILL.curtain} />
      <path
        d="M2 2 L8 0 L4 77 L-2 80 Z"
        className="fill-none stroke-scene-metal-dark/30"
        strokeWidth="0.3"
      />
      {FOLDS.map((x) => (
        <path
          key={x}
          d={`M${x + 1} 3 L${x - 3} 77`}
          className="stroke-scene-curtain-fold/60"
          strokeWidth="0.5"
        />
      ))}
      <path
        d="M1 1 L9 -1 L6 6"
        className="fill-none stroke-scene-metal"
        strokeWidth="0.7"
      />
      <path
        d="M-2 80 L4 77"
        className="stroke-scene-curtain-fold"
        strokeWidth="0.8"
      />
    </g>
  );
}
