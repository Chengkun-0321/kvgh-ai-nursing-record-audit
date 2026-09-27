import type { Metadata } from "next";
import type { ReactNode } from "react";

import { Providers } from "@/components/Providers";

import "./globals.css";

export const metadata: Metadata = {
  title: "護理稽核系統｜高榮 AI 護理紀錄稽核",
  description: "護理紀錄完整性與一致性稽核提醒",
};

type RootLayoutProps = {
  children: ReactNode;
};

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="zh-Hant" className="h-full antialiased">
      <body className="min-h-full bg-canvas font-sans text-body text-ink">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
