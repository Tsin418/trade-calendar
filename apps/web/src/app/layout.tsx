import type { Metadata } from "next";
import "./globals.css";

import { PreferencesProvider } from "@/components/preferences-context";

export const metadata: Metadata = {
  title: "交易日历 · Market Pulse",
  description: "面向个人交易准备的动态市场事件日历",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return <html lang="zh-CN"><body><PreferencesProvider>{children}</PreferencesProvider></body></html>;
}
