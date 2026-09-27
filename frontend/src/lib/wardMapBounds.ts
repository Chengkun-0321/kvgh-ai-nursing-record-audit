import { MAP_LIMITS, type MapBounds } from "./wardMap";

/** 固定標題、狀態列與詳情卡不屬於地圖，焦點移動需保留它們占用的空間。 */
export function measureMapBounds(viewport: HTMLElement): MapBounds {
  const stage = viewport.parentElement ?? viewport;
  const panel = stage.querySelector<HTMLElement>("[data-map-detail]");
  const title = stage.querySelector<HTMLElement>(".ward-title");
  const status = stage.querySelector<HTMLElement>(".ward-status");
  const pad = MAP_LIMITS.focusPaddingPx;
  const right =
    viewport.clientWidth -
    (panel ? panel.offsetWidth + MAP_LIMITS.panelGapPx : pad);
  return {
    left: pad,
    top: (title?.offsetHeight ?? 0) + pad,
    right: Math.max(pad * 2, right),
    bottom: Math.max(
      pad * 2,
      (status?.offsetTop ?? viewport.clientHeight) - pad,
    ),
  };
}
