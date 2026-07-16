import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ADGE v3.1",
  description: "Adaptive Delta-Gamma Engine — analytical tool, not investment advice",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ar" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
