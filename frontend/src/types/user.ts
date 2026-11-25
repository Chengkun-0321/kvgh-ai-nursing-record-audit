import type { AuthSession } from "./auth";

/** 目前登入的使用者；demo 登入只有帳號，後端尚未提供姓名與角色。 */
export type CurrentUser = AuthSession;
