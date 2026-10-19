"use client";
import { useState, type ReactNode } from "react";
import { Sidebar } from "./sidebar";
import { TopBar } from "./top-bar";
import { useSession } from "@/components/providers/session-provider";
import { cx } from "@/components/ui/primitives";
export function AppShell({
  title,
  children,
  counts,
}: {
  title: string;
  children: ReactNode;
  counts?: { mine: number; unassigned: number };
}) {
  const [open, setOpen] = useState(false),
    [collapsed, setCollapsed] = useState(false);
  const { session, preview, loading } = useSession();
  const toggle = () => {
    if (window.innerWidth < 1000) setOpen((v) => !v);
    else setCollapsed((v) => !v);
  };
  if (loading || !session)
    return (
      <div className="session-loading">
        <span className="loading-dot" />
        กำลังโหลดพื้นที่ทำงาน...
      </div>
    );
  return (
    <div className={cx("app-shell", collapsed && "sidebar-collapsed")}>
      <Sidebar
        open={open}
        onClose={() => {
          if (window.innerWidth < 1000) setOpen(false);
          else setCollapsed(true);
        }}
        counts={counts}
      />
      <div className="app-main">
        <TopBar title={title} onToggle={toggle} />
        {preview && (
          <div className="preview-banner">
            DESIGN PREVIEW · ข้อมูลตัวอย่างสำหรับตรวจหน้าตา
            ไม่มีการบันทึกลงฐานข้อมูล
          </div>
        )}
        <main id="main-content" className="page-content">
          {children}
        </main>
      </div>
    </div>
  );
}
