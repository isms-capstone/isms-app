import type { Metadata } from "next";
import "@fontsource/sarabun/400.css";
import "@fontsource/sarabun/500.css";
import "@fontsource/sarabun/600.css";
import "@fontsource/sarabun/700.css";
import "./globals.css";
import { SessionProvider } from "@/components/providers/session-provider";
export const metadata: Metadata = {
  title: { default: "Deverhood HT · ISMS", template: "%s · ISMS" },
  description: "Case Management & Service Operations",
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="th">
      <body>
        <a href="#main-content" className="skip-link">
          ข้ามไปเนื้อหา
        </a>
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
