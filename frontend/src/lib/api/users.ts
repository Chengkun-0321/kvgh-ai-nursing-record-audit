import type { CurrentUser } from "@/types/user";

// 完全虛構的展示使用者
const MOCK_CURRENT_USER: CurrentUser = { name: "林小美", role: "nurse" };

/**
 * 取得目前登入的使用者。
 *
 * TODO(待決): 登入與權限機制確定後改為讀取登入狀態，目前回傳虛構使用者。
 */
export async function getCurrentUser(): Promise<CurrentUser> {
  return MOCK_CURRENT_USER;
}
