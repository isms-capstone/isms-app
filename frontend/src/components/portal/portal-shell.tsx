"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Activity, ClipboardList, LogOut, Plus } from "lucide-react";
import { CompanyMark } from "@/components/layout/sidebar";
import { Button, cx } from "@/components/ui/primitives";

export type PortalMe = {
  name: string;
  organization: string;
  scope: "own" | "organization";
  systems: { id: number; name: string; product: string }[];
};

/** Fetch a customer portal resource through the server proxy (cookie session). */
export async function portalApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/portal/self/${path}`, { ...init, cache: "no-store" });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(
      typeof data?.detail === "string" ? data.detail : "ระบบขัดข้องชั่วคราว กรุณาลองใหม่",
    ) as Error & { status?: number };
    error.status = response.status;
    throw error;
  }
  return data as T;
}

/** Current customer; sends the visitor to sign-in when the session is missing or expired. */
export function usePortalMe() {
  const router = useRouter();
  const [me, setMe] = useState<PortalMe | null>(null);
  const load = useCallback(() => {
    portalApi<PortalMe>("me")
      .then(setMe)
      .catch((error: Error & { status?: number }) => {
        if (error.status === 401) router.replace("/portal/login");
      });
  }, [router]);
  useEffect(() => {
    const timer = setTimeout(load, 0);
    return () => clearTimeout(timer);
  }, [load]);
  return me;
}

export function PortalShell({
  me,
  children,
  public: isPublic = false,
}: {
  me?: PortalMe | null;
  children: ReactNode;
  public?: boolean;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const nav = [
    { href: "/portal", label: "เคสของฉัน", icon: ClipboardList },
    { href: "/portal/new", label: "แจ้งปัญหาใหม่", icon: Plus },
    { href: "/portal/status", label: "สถานะระบบ", icon: Activity },
  ];
  async function logout() {
    await fetch("/api/portal/auth/logout", { method: "POST" }).catch(() => null);
    router.replace("/portal/login");
  }
  return (
    <main id="main-content" className="portal-page min-h-screen">
      <header className="portal-top-bar">
        <Link href="/portal" className="portal-brand">
          <CompanyMark />
          <span>
            <strong>Deverhood HT</strong>
            <small>ศูนย์ช่วยเหลือลูกค้า</small>
          </span>
        </Link>
        {!isPublic || me ? (
          <nav aria-label="เมนูศูนย์ช่วยเหลือ" className="portal-nav">
            {nav.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className={cx("portal-nav-item", pathname === href && "active")}
                aria-current={pathname === href ? "page" : undefined}
              >
                <Icon size={16} aria-hidden />
                {label}
              </Link>
            ))}
          </nav>
        ) : (
          <nav aria-label="เมนูศูนย์ช่วยเหลือ" className="portal-nav">
            <Link href="/portal/login" className="portal-nav-item">
              เข้าสู่ระบบเพื่อติดตามเคส
            </Link>
          </nav>
        )}
        {me && (
          <div className="portal-account">
            <span>
              <strong>{me.name}</strong>
              <small>{me.organization}</small>
            </span>
            <Button variant="ghost" size="icon" aria-label="ออกจากระบบ" onClick={logout}>
              <LogOut size={16} />
            </Button>
          </div>
        )}
      </header>
      <div className="portal-content">{children}</div>
    </main>
  );
}
