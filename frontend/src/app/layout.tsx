import type { Metadata } from "next";
import "@DeverhoodHT/get-design/css";
import "@/styles/company-theme.css";
import "@fontsource/sarabun/400.css";
import "@fontsource/sarabun/500.css";
import "@fontsource/sarabun/600.css";
import "@fontsource/sarabun/700.css";
import "./globals.css";
import "@/styles/operations-ui.css";
import { SessionProvider } from "@/components/providers/session-provider";
import { CompanyProvider } from "@/components/providers/company-provider";
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
