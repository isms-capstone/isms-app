"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/primitives";
import { useSession } from "@/components/providers/session-provider";
import { api } from "@/lib/api";
import { routingDate } from "@/lib/routing-types";
type Notice = {
  id: number;
  ticket_id: number;
  message: string;
  created_at: string;
  read_at: string | null;
};
export function Notifications() {
  const { session, preview, href } = useSession(),
    router = useRouter();
  const [rows, setRows] = useState<Notice[]>([]),
    [open, setOpen] = useState(false),
    [error, setError] = useState(""),
    [retry, setRetry] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!session || preview) return;
    const c = new AbortController();
    const load = () =>
      api<Notice[]>("/routing/notifications", { signal: c.signal })
        .then((r) => {
          setRows(r);
          setError("");
        })
        .catch((e) => {
          if (!c.signal.aborted) setError(e.message);
        });
    void load();
    const timer = setInterval(load, 60000);
    return () => {
      c.abort();
      clearInterval(timer);
    };
  }, [session, preview, retry]);
  useEffect(() => {
    if (!open) return;
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        root.current?.querySelector<HTMLButtonElement>("button")?.focus();
      }
    };
    const click = (e: MouseEvent) => {
      if (!root.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", key);
    document.addEventListener("mousedown", click);
    return () => {
      document.removeEventListener("keydown", key);
      document.removeEventListener("mousedown", click);
    };
  }, [open]);
  const unread = rows.filter((r) => !r.read_at).length;
  async function read(row: Notice) {
    try {
      if (!row.read_at)
        await api(`/routing/notifications/${row.id}/read`, { method: "POST" });
      setRows((r) =>
        r.map((n) =>
          n.id === row.id ? { ...n, read_at: new Date().toISOString() } : n,
        ),
      );
      setOpen(false);
      router.push(href(`/cases/${row.ticket_id}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "เปิดแจ้งเตือนไม่สำเร็จ");
    }
  }
  return (
    <div className="routing-notifications" ref={root}>
      <Button
        variant="ghost"
        size="icon"
        aria-label={`การแจ้งเตือน ${unread} รายการยังไม่อ่าน`}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <Bell size={19} />
        {unread > 0 && <span className="routing-notice-count">{unread}</span>}
      </Button>
      {open && (
        <section
          className="routing-notice-popover"
          aria-label="รายการแจ้งเตือน"
        >
          <h2>การแจ้งเตือน</h2>
          <p className="routing-note">ล่าสุด 50 รายการ · อัปเดตทุก 60 วินาที</p>
          {error ? (
            <>
              <p role="alert" className="routing-error">
                {error}
              </p>
              <Button onClick={() => setRetry((n) => n + 1)}>
                ลองอีกครั้ง
              </Button>
            </>
          ) : !rows.length ? (
            <p className="routing-note">ยังไม่มีการแจ้งเตือน</p>
          ) : (
            <ul>
              {rows.map((r) => (
                <li key={r.id}>
                  <button
                    className={r.read_at ? "" : "is-unread"}
                    onClick={() => read(r)}
                  >
                    <span>{r.message}</span>
                    <time>{routingDate(r.created_at)}</time>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </div>
  );
}
