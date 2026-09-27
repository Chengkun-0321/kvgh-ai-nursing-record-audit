import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // AGENTS.md 是 CLAUDE.md 的 symlink，避免 next dev 自動寫入英文區塊；對應提醒已寫在 CLAUDE.md
  agentRules: false,
};

export default nextConfig;
