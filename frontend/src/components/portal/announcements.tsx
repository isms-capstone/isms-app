"use client";
import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { formatDateTime } from "@/lib/format";

type Notice = { id: number; title: string; message: string; product: string | null; created_at: string };

/** Public service status (POR-10). */
export function Announcements({ compact = false }: { compact?: boolean }) {
  const [notices, setNotices] = useState<Notice[] | null>(null);
  useEffect(() => {
    let active = true;
    const load = () =>
      fetch("/api/portal/self/announcements", { cache: "no-store" })
        .then((response) => (response.ok ? response.json() : []))
        .then((rows) => active && setNotices(rows))
        .catch(() => active && setNotices([]));
    const first = setTimeout(load, 0);
    const timer = setInterval(load, 60000);
    return () => {
      active = false;
      clearTimeout(first);
      clearInterval(timer);
    };
  }, []);
  if (!notices) return null;
  if (!notices.length)
    return compact ? null : (
      <p className="portal-status-ok" role="status">
        <CheckCircle2 size={18} aria-hidden /> ทุกระบบทำงานปกติ ไม่มีเหตุขัดข้องที่ประกาศไว้
      </p>
    );
  return (
    <section aria-label="ประกาศเหตุขัดข้อง" className="portal-notices">
      {notices.map((notice) => (
        <article key={notice.id} className="portal-notice" role="alert">
          <AlertTriangle size={18} aria-hidden />
          <div>
            <strong>
              {notice.product ? `${notice.product}: ` : ""}
              {notice.title}
            </strong>
            <p>{notice.message}</p>
            <small>ประกาศเมื่อ {formatDateTime(notice.created_at)} · ทีมกำลังดำเนินการ ไม่ต้องแจ้งเรื่องเดียวกันซ้ำ</small>
          </div>
        </article>
      ))}
    </section>
  );
}
