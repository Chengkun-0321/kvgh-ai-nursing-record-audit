import {
  clampCamera,
  getInitialCamera,
  getKeyCommand,
  getPointerPair,
  getRevealDelta,
  getScaleRange,
  getWheelZoomFactor,
  getZoomAvailability,
  INITIAL_CAMERA,
  MAP_LIMITS,
  type MapCamera,
  type MapPoint,
  type MapSize,
  type ScaleRange,
  zoomAt,
} from "./wardMap";
import {
  type MapMetrics,
  measureMapBounds,
  measureMapMetrics,
} from "./wardMapBounds";

type MapElements = {
  viewport: HTMLElement;
  world: HTMLElement;
  onScale: (scale: number) => void;
  /** 視窗或病房尺寸改變時通知新的縮放範圍（不在每次重繪時觸發）。 */
  onScaleRange: (range: ScaleRange) => void;
  onBackgroundClick: () => void;
  /** 每次重繪（已在 rAF 內）同步通知 3D 相機，DOM 疊層與場景才會在同一幀移動。 */
  onPaint: (camera: MapCamera) => void;
};

// 以 duration 0、fill forwards 的 Web Animation 寫入樣式，不使用 React inline style
const STILL: KeyframeAnimationOptions = { duration: 0, fill: "forwards" };

/** 原生指標事件管理地圖，繪製使用 Web Animations，不將座標寫入 React inline style。 */
export class WardMapController {
  private camera = { ...INITIAL_CAMERA };
  private range: ScaleRange = { min: 0, max: MAP_LIMITS.maxScale };
  private worldSize: MapSize = { width: 0, height: 0 };
  private cachedMetrics?: MapMetrics;
  private pointers = new Map<number, MapPoint>();
  private origin: MapPoint = { x: 0, y: 0 };
  private dragged = false;
  private hasInitialView = false;
  private frame = 0;
  private paintedScale?: number;
  private movingTimer = 0;
  private painting?: Animation;
  private scaling?: Animation;
  private sizing?: Animation;
  private observer: ResizeObserver;
  private abort = new AbortController();

  constructor(private elements: MapElements) {
    this.bind();
    this.observer = new ResizeObserver(() => this.refreshBounds());
    this.observer.observe(elements.viewport);
  }

  /**
   * 視窗幾何（安全區、詳情卡遮擋）的快取：指標與滾輪等高頻事件只讀快取，
   * 在手勢開始、尺寸改變、選床或關卡時才重新量測，避免每次事件都強制 layout。
   */
  private get metrics(): MapMetrics {
    this.cachedMetrics ??= measureMapMetrics(this.elements.viewport);
    return this.cachedMetrics;
  }

  private invalidate() {
    this.cachedMetrics = undefined;
  }

  /** 設定場景的地圖尺寸（px，100% 縮放）；第一次設定時套用初始視野。 */
  setWorldSize(size: MapSize) {
    this.worldSize = size;
    this.sizing?.cancel();
    this.sizing = this.elements.world.animate(
      [{ width: `${size.width}px`, height: `${size.height}px` }],
      STILL,
    );
    this.refreshBounds();
  }

  /** 重算縮放範圍；原本已縮到最小時，視窗改變後仍維持完整顯示整個病房。 */
  private updateRange() {
    const wasAtMin = !getZoomAvailability(this.camera.scale, this.range)
      .canZoomOut;
    this.range = getScaleRange(this.metrics.fit, this.worldSize);
    if (wasAtMin) this.camera = { ...this.camera, scale: this.range.min };
    this.elements.onScaleRange(this.range);
  }

  private refreshBounds() {
    this.invalidate();
    if (this.worldSize.width === 0) return;
    this.updateRange();
    if (!this.hasInitialView) {
      this.hasInitialView = true;
      this.reset();
      return;
    }
    const selected = this.elements.world.querySelector<HTMLElement>(
      '[data-bed-code][aria-pressed="true"]',
    );
    if (selected) this.reveal(selected);
    else this.move(this.camera);
  }

  private local(event: { clientX: number; clientY: number }): MapPoint {
    const { clientOrigin } = this.metrics;
    return {
      x: event.clientX - clientOrigin.x,
      y: event.clientY - clientOrigin.y,
    };
  }

  private move(camera: MapCamera) {
    this.camera = clampCamera(
      camera,
      this.metrics.pan,
      this.worldSize,
      this.range,
    );
    cancelAnimationFrame(this.frame);
    this.frame = requestAnimationFrame(() => this.paint());
  }

  private paint() {
    const { x, y, scale } = this.camera;
    this.painting?.cancel();
    this.painting = this.elements.world.animate(
      [{ transform: `translate(${x}px, ${y}px) scale(${scale})` }],
      STILL,
    );
    if (scale !== this.paintedScale) this.paintScale(scale);
    this.elements.onPaint(this.camera);
  }

  /** 倍率改變時才更新：--map-scale 讓床號標籤反向縮放、字級不變，純平移時標籤不必重算樣式。 */
  private paintScale(scale: number) {
    const { world } = this.elements;
    this.paintedScale = scale;
    this.scaling?.cancel();
    this.scaling = world.animate([{ "--map-scale": String(scale) }], STILL);
    const zoom = scale < MAP_LIMITS.compactLabelScale ? "compact" : "regular";
    if (world.dataset.zoom !== zoom) world.dataset.zoom = zoom;
    this.elements.onScale(scale);
  }

  /** 平移縮放期間標記 data-moving（CSS 暫停玻璃模糊）；停止後移除，並於下次手勢重新量測。 */
  private markMoving() {
    const { dataset } = this.elements.viewport;
    if (!dataset.moving) dataset.moving = "true";
    window.clearTimeout(this.movingTimer);
    this.movingTimer = window.setTimeout(() => {
      delete dataset.moving;
      this.invalidate();
    }, MAP_LIMITS.movingIdleMs);
  }

  private panBy(dx: number, dy: number, camera = this.camera) {
    this.move({ ...camera, x: camera.x + dx, y: camera.y + dy });
  }

  /** 工具列與鍵盤共用同一縮放入口。 */
  zoom(factor: number, point?: MapPoint) {
    const { x, y, width, height } = this.metrics.pan;
    const anchor = point ?? { x: x + width / 2, y: y + height / 2 };
    this.move(zoomAt(this.camera, anchor, factor, this.range));
  }

  /** 遮擋範圍改變（例如關閉詳情卡）後重新夾限，病房外不留空白。 */
  refresh() {
    if (!this.hasInitialView) return;
    this.invalidate();
    this.move(this.camera);
  }

  /** 回到整個病房剛好填滿安全區的初始視野。 */
  reset() {
    this.move(getInitialCamera(this.metrics.fit, this.worldSize));
  }

  /** 選取或鍵盤聚焦的病床保持可見，包括右側詳情卡遮住的區域。 */
  reveal(target: HTMLElement) {
    this.invalidate();
    const { x, y } = this.metrics.clientOrigin;
    const rect = target.getBoundingClientRect();
    const delta = getRevealDelta(
      {
        left: rect.left - x,
        top: rect.top - y,
        right: rect.right - x,
        bottom: rect.bottom - y,
      },
      measureMapBounds(this.elements.viewport, this.metrics),
    );
    this.panBy(delta.x, delta.y);
  }

  private onDown = (event: PointerEvent) => {
    if (event.button !== 0) return;
    if (this.pointers.size === 0) this.invalidate();
    const point = this.local(event);
    if (this.pointers.size === 0) {
      this.dragged = false;
      this.origin = point;
    }
    this.pointers.set(event.pointerId, point);
    if (this.pointers.size > 1) this.dragged = true;
    const target =
      event.target instanceof Element ? event.target.closest("button") : null;
    (target ?? this.elements.viewport).setPointerCapture(event.pointerId);
  };

  private onMove = (event: PointerEvent) => {
    const previous = this.pointers.get(event.pointerId);
    if (!previous) return;
    const before = getPointerPair([...this.pointers.values()]);
    const point = this.local(event);
    this.pointers.set(event.pointerId, point);
    const after = getPointerPair([...this.pointers.values()]);
    if (before && after) {
      this.pinch(before, after);
      return;
    }
    if (
      Math.hypot(point.x - this.origin.x, point.y - this.origin.y) >
      MAP_LIMITS.dragThresholdPx
    )
      this.dragged = true;
    if (!this.dragged) return;
    const { dataset } = this.elements.viewport;
    if (!dataset.dragging) dataset.dragging = "true";
    this.markMoving();
    this.panBy(point.x - previous.x, point.y - previous.y);
  };

  private pinch(
    before: NonNullable<ReturnType<typeof getPointerPair>>,
    after: NonNullable<ReturnType<typeof getPointerPair>>,
  ) {
    this.dragged = true;
    this.markMoving();
    const camera = zoomAt(
      this.camera,
      before.center,
      after.distance / before.distance,
      this.range,
    );
    const { center } = after;
    this.panBy(center.x - before.center.x, center.y - before.center.y, camera);
  }

  private onUp = (event: PointerEvent) => {
    if (event.type === "pointercancel") this.dragged = true;
    this.pointers.delete(event.pointerId);
    delete this.elements.viewport.dataset.dragging;
    // 雙指放開後以剩餘手指重建起點，避免下一次移動突然跳位。
    this.origin = [...this.pointers.values()][0] ?? this.origin;
  };

  private onClick = (event: MouseEvent) => {
    if (this.dragged && event.detail !== 0) {
      event.preventDefault();
      event.stopPropagation();
      return;
    }
    if (event.target instanceof Element && !event.target.closest("button")) {
      this.elements.onBackgroundClick();
    }
  };

  private onWheel = (event: WheelEvent) => {
    // 保留瀏覽器的 Ctrl／Command 縮放；普通滾輪只作用於病房。
    if (event.ctrlKey || event.metaKey) return;
    event.preventDefault();
    this.markMoving();
    const factor = getWheelZoomFactor(
      event.deltaY,
      event.deltaMode,
      this.elements.viewport.clientHeight,
    );
    this.zoom(factor, this.local(event));
  };

  private onKey = (event: KeyboardEvent) => {
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const command = getKeyCommand(event.key);
    if (!command) return;
    event.preventDefault();
    this.invalidate();
    if (command.type === "zoom") this.zoom(command.factor);
    if (command.type === "reset") this.reset();
    if (command.type !== "pan") return;
    const { direction } = command;
    const step = MAP_LIMITS.panStepPx;
    this.panBy(direction.x * step, direction.y * step);
  };

  private onFocus = (event: FocusEvent) => {
    if (this.pointers.size > 0) return;
    if (
      event.target instanceof HTMLElement &&
      event.target.matches("[data-bed-code]")
    )
      this.reveal(event.target);
  };

  private bind() {
    const { viewport } = this.elements;
    const options = { signal: this.abort.signal };
    viewport.addEventListener("pointerdown", this.onDown, options);
    viewport.addEventListener("pointermove", this.onMove, options);
    viewport.addEventListener("pointerup", this.onUp, options);
    viewport.addEventListener("pointercancel", this.onUp, options);
    viewport.addEventListener("lostpointercapture", this.onUp, options);
    viewport.addEventListener("click", this.onClick, {
      ...options,
      capture: true,
    });
    viewport.addEventListener("wheel", this.onWheel, {
      ...options,
      passive: false,
    });
    viewport.addEventListener("keydown", this.onKey, options);
    viewport.addEventListener("focusin", this.onFocus, options);
  }

  /** 元件卸載時移除原生監聽與動畫，避免 Strict Mode 重複註冊。 */
  destroy() {
    this.abort.abort();
    this.observer.disconnect();
    cancelAnimationFrame(this.frame);
    window.clearTimeout(this.movingTimer);
    this.painting?.cancel();
    this.scaling?.cancel();
    this.sizing?.cancel();
  }
}
