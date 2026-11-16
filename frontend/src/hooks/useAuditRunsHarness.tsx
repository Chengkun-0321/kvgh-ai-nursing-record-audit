import { act } from "react";
import { createRoot, type Root } from "react-dom/client";

/**
 * 測試用的最小 hook 包裝（不依賴 @testing-library/react，因其需要未核准的 @testing-library/dom）。
 * 只供測試檔引用，不會進入正式頁面。
 */
export type HookHarness<P, T> = {
  readonly current: T;
  rerender: (props: P) => Promise<void>;
  unmount: () => Promise<void>;
};

type ProbeProps<P, T> = {
  useTarget: (props: P) => T;
  props: P;
  onValue: (value: T) => void;
};

function Probe<P, T>({ useTarget, props, onValue }: ProbeProps<P, T>): null {
  onValue(useTarget(props));
  return null;
}

function markActEnvironment(): void {
  (
    globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }
  ).IS_REACT_ACT_ENVIRONMENT = true;
}

/** 掛載 hook 並回傳可讀取最新值、可重新渲染（換 props）與卸載的控制器。 */
export async function renderHookHarness<P, T>(
  useTarget: (props: P) => T,
  initialProps: P,
): Promise<HookHarness<P, T>> {
  markActEnvironment();
  const container = document.createElement("div");
  document.body.appendChild(container);
  const root: Root = createRoot(container);
  const box: { value?: T } = {};
  const onValue = (value: T) => {
    box.value = value;
  };
  const render = (props: P) =>
    act(async () => {
      root.render(
        <Probe useTarget={useTarget} props={props} onValue={onValue} />,
      );
    });

  await render(initialProps);
  return {
    get current(): T {
      if (box.value === undefined) {
        throw new Error("hook 尚未渲染");
      }
      return box.value;
    },
    rerender: render,
    unmount: () =>
      act(async () => {
        root.unmount();
        container.remove();
      }),
  };
}
