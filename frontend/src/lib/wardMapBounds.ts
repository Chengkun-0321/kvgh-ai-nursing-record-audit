import { MAP_LIMITS, type MapArea, type MapBounds } from "./wardMap";

// 安全區：病房場景鋪滿整個視窗，頂列、側欄與手機分頁列疊在場景上，以 CSS 定義扣除後的範圍
const SAFE_AREA_SELECTOR = ".ward-safe";

function getStage(viewport: HTMLElement): HTMLElement {
  return viewport.parentElement ?? viewport;
}

/** 右側詳情卡遮住的寬度（含間距）；沒開卡時為 0。 */
function getOccludedRight(viewport: HTMLElement): number {
  const panel =
    getStage(viewport).querySelector<HTMLElement>("[data-map-detail]");
  return panel ? panel.offsetWidth + MAP_LIMITS.panelGapPx : 0;
}

/**
 * 可放病房的區域（相對地圖視窗）：縮放範圍與初始視野用不扣詳情卡的版本，
 * 平移夾限扣掉詳情卡，開卡時右側病床仍可拖到卡片左側。
 */
export function measureMapArea(
  viewport: HTMLElement,
  { withDetail }: { withDetail: boolean },
): MapArea {
  const view = viewport.getBoundingClientRect();
  const safe =
    getStage(viewport)
      .querySelector<HTMLElement>(SAFE_AREA_SELECTOR)
      ?.getBoundingClientRect() ?? view;
  const occluded = withDetail ? getOccludedRight(viewport) : 0;
  return {
    x: safe.left - view.left,
    y: safe.top - view.top,
    width: Math.max(1, safe.width - occluded),
    height: Math.max(1, safe.height),
  };
}

/** 固定標題、狀態列與詳情卡不屬於地圖，焦點移動需保留它們占用的空間（相對地圖視窗）。 */
export function measureMapBounds(viewport: HTMLElement): MapBounds {
  const stage = getStage(viewport);
  const view = viewport.getBoundingClientRect();
  const area = measureMapArea(viewport, { withDetail: true });
  const title = stage.querySelector<HTMLElement>(".ward-title");
  const status = stage.querySelector<HTMLElement>(".ward-status");
  const pad = MAP_LIMITS.focusPaddingPx;
  const titleBottom = title
    ? title.getBoundingClientRect().bottom - view.top
    : area.y;
  const statusTop = status
    ? status.getBoundingClientRect().top - view.top
    : area.y + area.height;
  return {
    left: area.x + pad,
    top: titleBottom + pad,
    right: Math.max(area.x + pad * 2, area.x + area.width - pad),
    bottom: Math.max(titleBottom + pad * 2, statusTop - pad),
  };
}
