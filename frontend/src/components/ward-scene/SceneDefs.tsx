/** 場景共用漸層的參照；各床位 SVG 以 `fill={SCENE_FILL.xxx}` 使用。 */
export const SCENE_FILL = {
  wallFace: "url(#scene-wall-face)",
  panel: "url(#scene-panel)",
  woodTop: "url(#scene-wood-top)",
  woodFront: "url(#scene-wood-front)",
  curtain: "url(#scene-curtain)",
  softShadow: "url(#scene-soft-shadow)",
  lampGlow: "url(#scene-lamp-glow)",
  wallOcclusion: "url(#scene-wall-occlusion)",
} as const;

/**
 * 場景共用的 SVG 漸層定義，整頁只放一份（由 WardRoom 輸出），
 * 避免每個床位重複宣告相同 id。顏色一律取自 `@theme` 的 scene token。
 */
export function SceneDefs() {
  return (
    <svg aria-hidden="true" className="absolute size-0">
      <defs>
        <linearGradient id="scene-wall-face" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" className="[stop-color:var(--color-scene-wall)]" />
          <stop
            offset="1"
            className="[stop-color:var(--color-scene-wall-shade)]"
          />
        </linearGradient>
        <linearGradient id="scene-panel" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" className="[stop-color:var(--color-scene-panel)]" />
          <stop
            offset="1"
            className="[stop-color:var(--color-scene-panel-shade)]"
          />
        </linearGradient>
        <linearGradient id="scene-wood-top" x1="0" y1="0" x2="0" y2="1">
          <stop
            offset="0"
            className="[stop-color:var(--color-scene-wood-top)]"
          />
          <stop offset="1" className="[stop-color:var(--color-scene-wood)]" />
        </linearGradient>
        <linearGradient id="scene-wood-front" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" className="[stop-color:var(--color-scene-wood)]" />
          <stop
            offset="1"
            className="[stop-color:var(--color-scene-wood-shade)]"
          />
        </linearGradient>
        {/* 隔簾皺褶：水平重複的明暗條紋 */}
        <linearGradient
          id="scene-curtain"
          x1="0"
          y1="0"
          x2="0.34"
          y2="0"
          spreadMethod="repeat"
        >
          <stop
            offset="0"
            className="[stop-color:var(--color-scene-curtain)]"
          />
          <stop
            offset="0.6"
            className="[stop-color:var(--color-scene-curtain)]"
          />
          <stop
            offset="1"
            className="[stop-color:var(--color-scene-curtain-fold)]"
          />
        </linearGradient>
        {/* 牆腳的環境遮蔽：地面緊貼牆面處較暗，往外淡出 */}
        <linearGradient id="scene-wall-occlusion" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" className="[stop-color:var(--color-scene-shadow)]" />
          <stop
            offset="1"
            className="[stop-color:var(--color-scene-shadow)] [stop-opacity:0]"
          />
        </linearGradient>
        <radialGradient id="scene-soft-shadow">
          <stop offset="0" className="[stop-color:var(--color-scene-shadow)]" />
          <stop
            offset="1"
            className="[stop-color:var(--color-scene-shadow)] [stop-opacity:0]"
          />
        </radialGradient>
        <radialGradient id="scene-lamp-glow">
          <stop offset="0" className="[stop-color:var(--color-scene-lamp)]" />
          <stop
            offset="1"
            className="[stop-color:var(--color-scene-lamp)] [stop-opacity:0]"
          />
        </radialGradient>
      </defs>
    </svg>
  );
}
