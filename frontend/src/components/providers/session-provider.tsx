"use client";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Session } from "@/lib/types";
import { previewSession } from "@/lib/preview";
type Value = {
  session: Session | null;
  preview: boolean;
  loading: boolean;
  signOut: () => Promise<void>;
  href: (path: string) => string;
};
const SessionContext = createContext<Value | null>(null);
export function SessionProvider({ children }: { children: ReactNode }) {
  const pathname = usePathname(),
    router = useRouter();
  const preview = pathname.startsWith("/preview");
  const [session, setSession] = useState<Session | null>(null),
    [loading, setLoading] = useState(true);
  useEffect(() => {
    if (preview || pathname === "/login") return;
    let active = true;
    api<Session>("/registry/session")
      .then((data) => {
        if (active) setSession(data);
      })
      .catch(() => {
        if (active) router.replace("/login");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [preview, pathname, router]);
  useEffect(() => {
    const handler = () => {
      setSession(null);
      router.replace("/login");
    };
    window.addEventListener("isms:unauthorized", handler);
    return () => window.removeEventListener("isms:unauthorized", handler);
  }, [router]);
  const signOut = async () => {
    if (!preview) await fetch("/api/session", { method: "DELETE" });
    setSession(null);
    router.push("/login");
  };
  return (
    <SessionContext
      value={{
        session: preview ? previewSession : session,
        preview,
        loading: !preview && loading,
        signOut,
        href: (path) => `${preview ? "/preview" : ""}${path}`,
      }}
    >
      {children}
    </SessionContext>
  );
}
export function useSession() {
  const context = useContext(SessionContext);
  if (!context) throw new Error("SessionProvider required");
  return context;
}
