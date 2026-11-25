import { useRouter } from "next/navigation";

import { logout } from "@/lib/api/auth";
import { LOGIN_PATH } from "@/lib/auth";

import { useAsyncAction } from "./useAsyncAction";

/** 登出：呼叫後端清除登入 cookie 後回到登入頁；失敗時保留錯誤訊息供按鈕顯示。 */
export function useLogout() {
  const router = useRouter();
  const action = useAsyncAction();

  async function signOut() {
    const result = await action.run(logout);
    if (result.ok) {
      router.replace(LOGIN_PATH);
      router.refresh();
    }
  }

  return {
    isPending: action.isPending,
    errorMessage: action.errorMessage,
    signOut,
  };
}
