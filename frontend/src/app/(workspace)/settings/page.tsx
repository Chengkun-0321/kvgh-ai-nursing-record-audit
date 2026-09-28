import { redirect } from "next/navigation";

// 設定目前只有 LLM 模型一頁
export default function SettingsPage() {
  redirect("/settings/llm");
}
