// Vitest 共用設定：讓 React 的 act() 在 jsdom 中正常運作，並補上 jsdom 缺少的 API
Reflect.set(globalThis, "IS_REACT_ACT_ENVIRONMENT", true);

class NoopIntersectionObserver {
  readonly root = null;
  readonly rootMargin = "0px";
  readonly thresholds: readonly number[] = [];
  observe(): void {
    // 測試環境不需要觀察可見度
  }
  unobserve(): void {
    // 測試環境不需要觀察可見度
  }
  disconnect(): void {
    // 測試環境不需要觀察可見度
  }
  takeRecords(): IntersectionObserverEntry[] {
    return [];
  }
}

if (typeof globalThis.IntersectionObserver === "undefined") {
  Reflect.set(globalThis, "IntersectionObserver", NoopIntersectionObserver);
}

export {};
