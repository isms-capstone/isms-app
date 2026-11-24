"use client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ArrowLeft, MessageSquare } from "lucide-react";
import { StatusBadge } from "@/components/cases/case-badges";
import { PortalShell, portalApi, usePortalMe } from "@/components/portal/portal-shell";
import { formatDateTime } from "@/lib/format";

type CaseDetail = {
  ticket_no: string;
  subject: string;
  description: string | null;
  status: string;
  created_at: string;
  resolved_at: string | null;
  product: string | null;
  system: string | null;
  reporter: string | null;
  replies: { id: number; body: string; created_at: string }[];
  history: { status: string; status_label: string; at: string }[];
};

export default function PortalCase() {
  const { no } = useParams<{ no: string }>();
  const me = usePortalMe();
  const [data, setData] = useState<CaseDetail | null>(null),
    [error, setError] = useState("");
  useEffect(() => {
    if (!me) return;
    let active = true;
    const load = () =>
      portalApi<CaseDetail>(`me/cases/${encodeURIComponent(no)}`)
        .then((row) => active && (setData(row), setError("")))
        .catch((e: Error) => active && setError(e.message));
    const first = setTimeout(load, 0);
    const timer = setInterval(load, 15000);
    return () => {
      active = false;
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [me, no]);

  return (
    <PortalShell me={me}>
      <Link href="/portal" className="text-link portal-back">
        <ArrowLeft size={14} aria-hidden /> กลับไปรายการเคส
      </Link>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {data && (
        <div className="portal-case-layout">
          <section className="surface detail-card">
            <div className="portal-case-heading">
              <small>{data.ticket_no}</small>
              <StatusBadge status={data.status} />
            </div>
            <h1>{data.subject}</h1>
            {data.description && <p className="whitespace-pre-wrap">{data.description}</p>}
            <dl className="portal-facts">
              <div>
                <dt>ผลิตภัณฑ์</dt>
                <dd>
                  {data.system && data.product && data.system.startsWith(data.product)
                    ? data.system
                    : [data.product, data.system].filter(Boolean).join(" · ") || "—"}
                </dd>
              </div>
              <div>
                <dt>แจ้งเมื่อ</dt>
                <dd>{formatDateTime(data.created_at)}</dd>
              </div>
              {data.reporter && (
                <div>
                  <dt>ผู้แจ้ง</dt>
                  <dd>{data.reporter}</dd>
                </div>
              )}
              {data.resolved_at && (
                <div>
                  <dt>แก้ไขเสร็จเมื่อ</dt>
                  <dd>{formatDateTime(data.resolved_at)}</dd>
                </div>
              )}
            </dl>
            <h2 className="flex items-center gap-2">
              <MessageSquare size={17} aria-hidden /> ข้อความจากทีมสนับสนุน
            </h2>
            {data.replies.length === 0 ? (
              <p className="text-muted">ยังไม่มีข้อความตอบกลับ ทีมจะแจ้งที่นี่และทางอีเมลเมื่อมีความคืบหน้า</p>
            ) : (
              <ul className="portal-replies" aria-live="polite">
                {data.replies.map((reply) => (
                  <li key={reply.id}>
                    <small>{formatDateTime(reply.created_at)}</small>
                    <p className="whitespace-pre-wrap">{reply.body}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
          <aside className="surface detail-card">
            <h2>ความคืบหน้า</h2>
            <ol className="portal-history">
              <li>
                <strong>รับเรื่องแล้ว</strong>
                <small>{formatDateTime(data.created_at)}</small>
              </li>
              {data.history.map((step) => (
                <li key={`${step.status}-${step.at}`}>
                  <strong>{step.status_label}</strong>
                  <small>{formatDateTime(step.at)}</small>
                </li>
              ))}
            </ol>
            {data.status === "RESOLVED" && (
              <p className="field-hint">
                ทีมแก้ไขเรียบร้อยแล้ว หากยังพบปัญหาภายใน 14 วัน ให้แจ้งปัญหาใหม่โดยอ้างอิงเลขเคส {data.ticket_no}
              </p>
            )}
          </aside>
        </div>
      )}
    </PortalShell>
  );
}
