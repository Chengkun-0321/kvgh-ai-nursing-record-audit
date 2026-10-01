import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // AGENTS.md 是 CLAUDE.md 的 symlink，避免 next dev 自動寫入英文區塊；對應提醒已寫在 CLAUDE.md
  agentRules: false,
  // 由編譯器自動 memo 元件與 hooks，元件內不再手寫 useMemo／useCallback
  reactCompiler: true,
  // 壓縮會把經 proxy 的 SSE（text/event-stream）整段緩衝，測試對話就無法逐字顯示；
  // 對外網域由 Cloudflare 等前端代理壓縮
  compress: false,
  // 瀏覽器一律呼叫同網域的 /api/v1/*，由此轉給後端：不需開放 CORS，經對外網域也能使用。
  // `next build` 時就決定目標，改 API_BASE_URL 後需重新建置
  async rewrites() {
    const backendUrl = process.env.API_BASE_URL;
    if (!backendUrl) {
      return [];
    }
    return [
      { source: "/api/v1/:path*", destination: `${backendUrl}/api/v1/:path*` },
    ];
  },
};

export default nextConfig;
