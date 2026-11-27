import type { Metadata, Viewport } from "next";
import "@DeverhoodHT/get-design/css";
import "@/styles/company-theme.css";
import "./globals.css";
import "@/styles/operations-ui.css";
import "@/styles/company-layout.css";
import "@/styles/routing.css";
import "@/styles/work-category.css";
import "@/styles/similarity.css";
import "@/styles/case-controls.css";
import { SessionProvider } from "@/components/providers/session-provider";
import { CompanyProvider } from "@/components/providers/company-provider";
export const metadata: Metadata = {
  title: { default: "Deverhood HT · ISMS", template: "%s · ISMS" },
  description: "Case Management & Service Operations",
  applicationName: "ISMS",
  appleWebApp: { capable: true, title: "ISMS", statusBarStyle: "default" },
  icons: { icon: "/icons/icon-192.png", apple: "/icons/icon-192.png" },
};
export const viewport: Viewport = { themeColor: "#0b60ff" };
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="th" data-color-set="getx" data-theme="light">
      <body>
        <a href="#main-content" className="skip-link">
          ข้ามไปเนื้อหา
        </a>
        <CompanyProvider>
          <SessionProvider>{children}</SessionProvider>
        </CompanyProvider>
      </body>
    </html>
  );
}
