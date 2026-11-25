"use client";

import { type ReactNode, useEffect, useRef } from "react";

type SelectedScrollListProps = {
  /** 目前選取的項目；改變時重新捲動 */
  selectedKey: string | null;
  className?: string;
  children: ReactNode;
};

/**
 * 可捲動的清單：選取項目（`aria-current="page"`）不在可見範圍時，把它捲到清單中間。
 * 只捲清單本身，不用 `scrollIntoView`，避免連整個頁面一起捲動。
 */
export function SelectedScrollList({
  selectedKey,
  className,
  children,
}: SelectedScrollListProps) {
  const listRef = useRef<HTMLUListElement>(null);

  useEffect(() => {
    const list = listRef.current;
    const selected = list?.querySelector<HTMLElement>('[aria-current="page"]');
    if (!list || !selected) {
      return;
    }
    const listBox = list.getBoundingClientRect();
    const itemBox = selected.getBoundingClientRect();
    const isVisible =
      itemBox.top >= listBox.top && itemBox.bottom <= listBox.bottom;
    if (!isVisible) {
      // 項目在清單內容中的位置＝相對清單可視區的位置＋目前捲動量
      const top = itemBox.top - listBox.top + list.scrollTop;
      list.scrollTop = top - (list.clientHeight - itemBox.height) / 2;
    }
  }, [selectedKey]);

  return (
    <ul ref={listRef} className={className}>
      {children}
    </ul>
  );
}
