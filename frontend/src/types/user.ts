// TODO(待決): 登入與權限機制確定後，改用後端回傳的使用者型別

export type UserRole = "nurse" | "head_nurse";

export type CurrentUser = {
  name: string;
  role: UserRole;
};
