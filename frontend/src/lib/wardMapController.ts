import {
  clampCamera,
  getInitialCamera,
  getKeyCommand,
  getPointerPair,
  getRevealOffset,
  getWheelZoomFactor,
  INITIAL_CAMERA,
  MAP_LIMITS,
  type MapCamera,
  type MapPoint,
  type MapSize,
  zoomAt,
} from "./wardMap";
import { measureMapBounds } from "./wardMapBounds";

type MapElements = {
  viewport: HTMLElement;
  world: HTMLElement;
  onScale: (scale: number) => void;
  onBackgroundClick: () => void;
  /** 每次重繪（已在 rAF 內）同步通知 3D 相機，DOM 疊層與場景才會在同一幀移動。 */
  onPaint: (camera: MapCamera) => void;
};

/** 原生指標事件管理地圖，繪製使用 Web Animations，不將座標寫入 React inline style。 */
export class WardMapController {
  private camera = { ...INITIAL_CAMERA };
  private pointers = new Map<number, MapPoint>();
  private origin: MapPoint = { x: 0, y: 0 };
  private dragged = false;
  private hasInitialView = false;
  private frame = 0;
  private painting?: Animation;
  private sizing?: Animation;
  private observer: ResizeObserver;
  private abort = new AbortController();

  constructor(private elements: MapElements) {
    this.bind();
    this.observer = new ResizeObserver(() => this.refreshBounds());
    this.observer.observe(elements.viewport);
  }

  private get viewportSize() {
    const { viewport } = this.elements;
    const bounds = measureMapBounds(viewport);
    return { width: bounds.right, height: viewport.clientHeight };
  }

  private get worldSize(): MapSize {
    const { world } = this.elements;
    return { width: world.offsetWidth, height: world.offsetHeight };
  }

  /** 設定場景的地圖尺寸（px，100% 縮放）；第一次設定時套用初始視野。 */
  setWorldSize(size: MapSize) {
    this.sizing?.cancel();
    this.sizing = this.elements.world.animate(
      [{ width: `${size.width}px`, height: `${size.height}px` }],
      { duration: 0, fill: "forwards" },
    );
    this.refreshBounds();
  }

  private refreshBounds() {
    if (this.worldSize.width === 0) return;
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
    const rect = this.elements.viewport.getBoundingClientRect();
    return { x: event.clientX - rect.left, y: event.clientY - rect.top };
  }

  private move(camera: MapCamera) {
    this.camera = clampCamera(camera, this.viewportSize, this.worldSize);
    cancelAnimationFrame(this.frame);
    this.frame = requestAnimationFrame(() => this.paint());
  }

  private paint() {
    const { x, y, scale } = this.camera;
    this.painting?.cancel();
    // --map-scale 讓床號標籤反向縮放，縮放時字級維持不變
    this.painting = this.elements.world.animate(
      [
        {
          transform: `translate(${x}px, ${y}px) scale(${scale})`,
          "--map-scale": String(scale),
        },
      ],
      { duration: 0, fill: "forwards" },
    );
    this.elements.world.dataset.zoom =
      scale < MAP_LIMITS.compactLabelScale ? "compact" : "regular";
    this.elements.onScale(scale);
    this.elements.onPaint(this.camera);
  }

  /** 工具列與鍵盤共用同一縮放入口。 */
  zoom(factor: number, point?: MapPoint) {
    const { width, height } = this.viewportSize;
    this.move(
      zoomAt(this.camera, point ?? { x: width / 2, y: height / 2 }, factor),
    );
  }

  /** 回到整個病房置中的初始視野。 */
  reset() {
    const bounds = measureMapBounds(this.elements.viewport);
    this.move(getInitialCamera(bounds, this.worldSize));
  }

  /** 選取或鍵盤聚焦的病床保持可見，包括右側詳情卡遮住的區域。 */
  reveal(target: HTMLElement) {
    const view = this.elements.viewport.getBoundingClientRect();
    const rect = target.getBoundingClientRect();
    const bounds = measureMapBounds(this.elements.viewport);
    this.move({
      ...this.camera,
      x:
        this.camera.x +
        getRevealOffset(
          rect.left - view.left,
          rect.right - view.left,
          bounds.left,
          bounds.right,
        ),
      y:
        this.camera.y +
        getRevealOffset(
          rect.top - view.top,
          rect.bottom - view.top,
          bounds.top,
          bounds.bottom,
        ),
    });
  }

  private onDown = (event: PointerEvent) => {
    if (event.button !== 0) return;
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
    this.elements.viewport.dataset.dragging = "true";
    this.move({
      ...this.camera,
      x: this.camera.x + point.x - previous.x,
      y: this.camera.y + point.y - previous.y,
    });
  };

  private pinch(
    before: NonNullable<ReturnType<typeof getPointerPair>>,
    after: NonNullable<ReturnType<typeof getPointerPair>>,
  ) {
    this.dragged = true;
    const camera = zoomAt(
      this.camera,
      before.center,
      after.distance / before.distance,
    );
    this.move({
      ...camera,
      x: camera.x + after.center.x - before.center.x,
      y: camera.y + after.center.y - before.center.y,
    });
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
    if (command.type === "zoom") this.zoom(command.factor);
    if (command.type === "reset") this.reset();
    if (command.type !== "pan") return;
    this.move({
      ...this.camera,
      x: this.camera.x + command.direction.x * MAP_LIMITS.panStepPx,
      y: this.camera.y + command.direction.y * MAP_LIMITS.panStepPx,
    });
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
    this.painting?.cancel();
    this.sizing?.cancel();
  }
}
