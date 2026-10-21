// 不依賴 @testing-library/dom 的最小渲染工具：createRoot + act，查詢用標準 DOM API
import { act, type ReactNode } from "react";
import { createRoot, type Root } from "react-dom/client";

type Mounted = { root: Root; container: HTMLDivElement };

const mounted: Mounted[] = [];

export async function render(ui: ReactNode): Promise<HTMLDivElement> {
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root = createRoot(container);
  mounted.push({ root, container });
  await act(async () => {
    root.render(ui);
  });
  return container;
}

export async function cleanup(): Promise<void> {
  for (const item of mounted.splice(0)) {
    await act(async () => {
      item.root.unmount();
    });
    item.container.remove();
  }
  document.body.innerHTML = "";
}

export async function click(element: Element): Promise<void> {
  await act(async () => {
    element.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  });
}

// 讓尚未完成的 promise 與 React 更新跑完
export async function flush(): Promise<void> {
  for (let round = 0; round < 3; round += 1) {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
  }
}

export function must<T>(value: T | null | undefined, label: string): T {
  if (value === null || value === undefined) {
    throw new Error(`找不到：${label}`);
  }
  return value;
}

export function cardOf(
  container: ParentNode,
  businessDate: string,
): HTMLElement {
  const selector = `article[data-business-date="${businessDate}"]`;
  return must(
    container.querySelector<HTMLElement>(selector),
    `${businessDate} 的卡片`,
  );
}

export function buttonIn(card: ParentNode): HTMLButtonElement | null {
  return card.querySelector("button");
}

export type Deferred<T> = {
  promise: Promise<T>;
  resolve: (value: T) => void;
  reject: (reason: unknown) => void;
};

// 可手動 resolve／reject 的 promise，用來控制請求進行中的狀態
export function deferred<T>(): Deferred<T> {
  let resolve: (value: T) => void = () => undefined;
  let reject: (reason: unknown) => void = () => undefined;
  const promise = new Promise<T>((onResolve, onReject) => {
    resolve = onResolve;
    reject = onReject;
  });
  return { promise, resolve, reject };
}
