import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ADGE — Adaptive Delta-Gamma Engine",
  description: "محرّك تحليل كمّي تعليمي لتركيبات الدلتا-غاما. ليست توصية استثمارية.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
