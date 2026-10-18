"use client";
import { LanguageProvider } from "@DeverhoodHT/get-design";
export function CompanyProvider({ children }: { children: React.ReactNode }) {
  return <LanguageProvider defaultLanguage="th">{children}</LanguageProvider>;
}
