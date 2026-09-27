"use client";

import { motion } from "motion/react";

import { SPRING_DEFAULT } from "@/lib/motion";
import { cn } from "@/lib/utils";

type SelectionIndicatorProps = {
  /** 同一組選項共用同一個 layoutId，選取底色才會在項目間以 spring 滑動 */
  layoutId: string;
  className?: string;
};

/** 選取中的底色或外框（分段控制器、狀態列、病床選取），裝飾用，對輔助科技隱藏。 */
export function SelectionIndicator({
  layoutId,
  className,
}: SelectionIndicatorProps) {
  return (
    <motion.span
      layoutId={layoutId}
      transition={SPRING_DEFAULT}
      aria-hidden="true"
      className={cn("absolute inset-0", className)}
    />
  );
}
