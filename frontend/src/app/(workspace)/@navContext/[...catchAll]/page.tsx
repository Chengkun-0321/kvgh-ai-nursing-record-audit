/**
 * 首頁以外的頁面不顯示頂部的病房資訊。站內換頁時，沒有對應頁面的平行路由會保留上一頁的內容，
 * 因此用 catch-all 對應所有其他路徑並回傳空內容。
 */
export default function NavContextOther() {
  return null;
}
