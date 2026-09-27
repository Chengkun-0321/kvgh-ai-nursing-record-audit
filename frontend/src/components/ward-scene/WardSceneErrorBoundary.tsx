"use client";

import { Component, type ReactNode } from "react";

type WardSceneErrorBoundaryProps = {
  children: ReactNode;
  onError: () => void;
};

type WardSceneErrorBoundaryState = { hasError: boolean };

/** 模型載入失敗或 WebGL 建立失敗時交給上層切換成 2D 版本（error boundary 只能用 class 元件）。 */
export class WardSceneErrorBoundary extends Component<
  WardSceneErrorBoundaryProps,
  WardSceneErrorBoundaryState
> {
  state: WardSceneErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): WardSceneErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.error("病房 3D 場景無法顯示，改用 2D 版本", error);
    this.props.onError();
  }

  render() {
    return this.state.hasError ? null : this.props.children;
  }
}
