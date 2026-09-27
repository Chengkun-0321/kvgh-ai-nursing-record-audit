import {
  MAP_LIMITS,
  type MapArea,
  type MapBounds,
  type MapPoint,
} from "./wardMap";

// 安全區：病房場景鋪滿整個視窗，側欄、使用者膠囊與手機頂列／分頁列疊在場景上，以 CSS 定義扣除後的範圍
const SAFE_AREA_SELECTOR = ".ward-safe";

function getStage(viewport: HTMLElement): HTMLElement {
  return viewport.parentElement ?? viewport;
}

/** 安全區扣掉 padding（病房適配留白）後的矩形；沒有安全區時退回整個地圖視窗。 */
function getFitRect(viewport: HTMLElement): DOMRectReadOnly {
  const safe =
    getStage(viewport).querySelector<HTMLElement>(SAFE_AREA_SELECTOR);
  if (!safe) return viewport.getBoundingClientRect();
  const rect = safe.getBoundingClientRect();
  const style = getComputedStyle(safe);
  const top = parseFloat(style.paddingTop);
  const left = parseFloat(style.paddingLeft);
  return new DOMRectReadOnly(
    rect.left + left,
    rect.top + top,
    rect.width - left - parseFloat(style.paddingRight),
    rect.height - top - parseFloat(style.paddingBottom),
  );
}

/**
 * 右側詳情卡遮住適配區域的寬度（含間距）；沒開卡時為 0。
 * 以版面位置（offsetLeft）計算，不受大卡進場的 transform 動畫影響。
 */
function getOccludedRight(viewport: HTMLElement, fit: DOMRectReadOnly): number {
  const panel =
    getStage(viewport).querySelector<HTMLElement>("[data-map-detail]");
  const container = panel?.offsetParent;
  if (!panel || !container) return 0;
  const panelLeft = container.getBoundingClientRect().left + panel.offsetLeft;
  return Math.max(0, fit.right - panelLeft + MAP_LIMITS.panelGapPx);
}

/** 一次量出的地圖視窗幾何；控制器快取到下一次尺寸或遮擋改變，高頻指標事件不必強制 layout。 */
export type MapMetrics = {
  /** 地圖視窗左上角的 client 座標，換算指標位置用。 */
  clientOrigin: MapPoint;
  /** 縮放範圍與初始視野：安全區扣適配留白，不扣詳情卡。 */
  fit: MapArea;
  /** 平移夾限：再扣掉詳情卡遮住的寬度，開卡時右側病床仍可拖到卡片左側。 */
  pan: MapArea;
};

/** 可放病房的區域（相對地圖視窗，已扣適配留白）。 */
export function measureMapMetrics(viewport: HTMLElement): MapMetrics {
  const view = viewport.getBoundingClientRect();
  const fit = getFitRect(viewport);
  const toArea = (occluded: number): MapArea => ({
    x: fit.left - view.left,
    y: fit.top - view.top,
    width: Math.max(1, fit.width - occluded),
    height: Math.max(1, fit.height),
  });
  return {
    clientOrigin: { x: view.left, y: view.top },
    fit: toArea(0),
    pan: toArea(getOccludedRight(viewport, fit)),
  };
}

/** 固定標題、狀態列與詳情卡不屬於地圖，焦點移動需保留它們占用的空間（相對地圖視窗）。 */
export function measureMapBounds(
  viewport: HTMLElement,
  { clientOrigin, pan: area }: MapMetrics,
): MapBounds {
  const stage = getStage(viewport);
  const title = stage.querySelector<HTMLElement>(".ward-title");
  const status = stage.querySelector<HTMLElement>(".ward-status");
  const pad = MAP_LIMITS.focusPaddingPx;
  const titleBottom = title
    ? title.getBoundingClientRect().bottom - clientOrigin.y
    : area.y;
  const statusTop = status
    ? status.getBoundingClientRect().top - clientOrigin.y
    : area.y + area.height;
  return {
    left: area.x + pad,
    top: titleBottom + pad,
    right: Math.max(area.x + pad * 2, area.x + area.width - pad),
    bottom: Math.max(titleBottom + pad * 2, statusTop - pad),
  };
}
