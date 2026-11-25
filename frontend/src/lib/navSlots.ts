/**
 * 頂部導覽中預留給頁面操作的插槽（例如首頁的「清單／3D 病房」切換）。
 * 頁面以 portal 把操作放進來，狀態仍由頁面自己持有；沒有內容時插槽不佔空間。
 */
export const NAV_PAGE_ACTIONS_SLOT_ID = {
  /** 桌機頂部導覽：右側狀態膠囊的左邊 */
  desktop: "nav-page-actions",
  /** 手機／平板頂列：使用者狀態的左邊 */
  mobile: "topbar-page-actions",
} as const;
