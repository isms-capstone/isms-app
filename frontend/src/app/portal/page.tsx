"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { Segment } from "@DeverhoodHT/get-design";
import { StatusBadge } from "@/components/cases/case-badges";
import { PortalShell, portalApi, usePortalMe } from "@/components/portal/portal-shell";
import { Announcements } from "@/components/portal/announcements";
import { EmptyState } from "@/components/ui/primitives";
import { formatDateTime } from "@/lib/format";

type PortalCase = {
  ticket_no: string;
  subject: string;
  status: string;
  created_at: string;
  product: string | null;
  reporter: string | null;
  replies: number;
};

export default function PortalHome() {
  const me = usePortalMe();
  const [filter, setFilter] = useState("open"),
    [cases, setCases] = useState<PortalCase[] | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    if (!me) return;
    let active = true;
    const load = () =>
      portalApi<PortalCase[]>(`me/cases?status=${filter}`)
        .then((rows) => active && (setCases(rows), setError("")))
        .catch((e: Error) => active && setError(e.message));
    const first = setTimeout(load, 0);
    const timer = setInterval(load, 30000);
    return () => {
      active = false;
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [me, filter]);

  return (
    <PortalShell me={me}>
      <Announcements compact />
      <div className="page-heading">
        <div>
          <h1>เคสของ{me?.scope === "organization" ? `องค์กร (${me.organization})` : "ฉัน"}</h1>
          <p>ติดตามสถานะและข้อความตอบกลับจากทีมสนับสนุน รายการอัปเดตทุก 30 วินาที</p>
        </div>
        <Link href="/portal/new" className="button button-primary">
          <Plus size={16} aria-hidden /> แจ้งปัญหาใหม่
        </Link>
      </div>
      <section className="surface detail-card">
        <Segment
          aria-label="สถานะเคส"
          value={filter}
          onChange={(value) => setFilter(String(value))}
          options={[
            { value: "open", label: "ยังไม่เสร็จ" },
            { value: "closed", label: "เสร็จแล้ว" },
            { value: "all", label: "ทั้งหมด" },
          ]}
        />
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        {cases && cases.length === 0 && (
          <EmptyState title="ไม่มีเคสในหมวดนี้" description="ถ้าพบปัญหา กด “แจ้งปัญหาใหม่” ได้เลย" />
        )}
        <ul className="portal-case-list">
          {cases?.map((item) => (
            <li key={item.ticket_no}>
              <Link href={`/portal/cases/${item.ticket_no}`} className="portal-case">
                <span className="portal-case-main">
                  <small>
                    {item.ticket_no} · {item.product || "ไม่ระบุผลิตภัณฑ์"} · แจ้งเมื่อ{" "}
                    {formatDateTime(item.created_at)}
                    {me?.scope === "organization" && item.reporter ? ` · ${item.reporter}` : ""}
                  </small>
                  <strong>{item.subject}</strong>
                </span>
                {item.replies > 0 && <span className="portal-reply-count">ตอบกลับ {item.replies}</span>}
                <StatusBadge status={item.status} />
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </PortalShell>
  );
}
