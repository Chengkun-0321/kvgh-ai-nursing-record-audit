import Image from "next/image";

import { BED_CARD_SPRITE_SIZE } from "@/lib/bedSprites";
import { cn } from "@/lib/utils";

type BedPhotoProps = {
  src: string;
  sizes: string;
  className?: string;
};

/** 病床寫實圖片（透明背景，狀態光暈已繪入素材）。僅為裝飾，不代表實際病患。 */
export function BedPhoto({ src, sizes, className }: BedPhotoProps) {
  return (
    <Image
      src={src}
      alt=""
      width={BED_CARD_SPRITE_SIZE.width}
      height={BED_CARD_SPRITE_SIZE.height}
      sizes={sizes}
      loading="lazy"
      draggable={false}
      className={cn("h-auto w-full select-none", className)}
    />
  );
}
