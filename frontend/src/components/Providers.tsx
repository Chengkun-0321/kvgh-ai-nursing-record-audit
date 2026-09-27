"use client";

import { MotionConfig } from "motion/react";
import type { ReactNode } from "react";

type ProvidersProps = {
  children: ReactNode;
};

/** 全站 client 端設定：尊重作業系統「減少動態」偏好。 */
export function Providers({ children }: ProvidersProps) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
