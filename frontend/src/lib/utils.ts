import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** 合併條件 class，並以 tailwind-merge 解決衝突的 utility。 */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
