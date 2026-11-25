import { cache } from "react";

import type { CurrentUser } from "@/types/user";

import { getSession } from "./auth";

/**
 * 取得目前登入的使用者（demo 登入只有帳號）。
 * 以 `cache` 包裝，同一次請求中外框重複呼叫只向後端取一次。
 */
export const getCurrentUser = cache((): Promise<CurrentUser> => getSession());
