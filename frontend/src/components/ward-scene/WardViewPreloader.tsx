"use client";

import { useEffect } from "react";

import { preloadWardView } from "@/lib/sceneAssets";
import { WARD_KITS, type WardKit } from "@/lib/wardKit";
import type { BedStatus } from "@/types/ward";

type WardViewPreloaderProps = {
  kit: WardKit;
  beds: readonly BedStatus[];
};

/**
 * 放在場景的 Suspense 內：目前視角的素材載完、畫面顯示後，才預載其他視角，
 * 不與首屏搶頻寬；切換正視／斜視時可立即顯示。
 */
export function WardViewPreloader({ kit, beds }: WardViewPreloaderProps) {
  useEffect(() => {
    for (const other of Object.values(WARD_KITS)) {
      if (other !== kit) preloadWardView(other, beds);
    }
  }, [kit, beds]);

  return null;
}
