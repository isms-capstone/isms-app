"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Megaphone } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import { TextArea, SelectControl } from "@/components/ui/company-fields";
import { Button, Input } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { Product } from "@/lib/types";

type Notice = {
  id: number;
  title: string;
  message: string;
  is_active: boolean;
  product: string | null;
  ticket_no: string | null;
  status_label: string | null;
  created_at: string;
  resolved_at: string | null;
};
const EDITORS = new Set(["Admin", "Team Lead"]);

/** POR-10: staff publish and close service status notices for the customer portal. */
export default function AnnouncementsPage() {
  const { session } = useSession();
  const [rows, setRows] = useState<Notice[]>([]),
    [products, setProducts] = useState<Product[]>([]),
    [title, setTitle] = useState(""),
    [message, setMessage] = useState(""),
    [ticketNo, setTicketNo] = useState(""),
    [product, setProduct] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const allowed = !!session && EDITORS.has(session.role);
  const load = useCallback(() => {
    if (!allowed) return;
    api<Notice[]>("/portal/announcements/manage").then(setRows).catch((e) => setError(e.message));
    api<Product[]>("/products?is_active=true&limit=100").then(setProducts).catch(() => null);
  }, [allowed]);
  useEffect(() => {
    const timer = setTimeout(load, 0);
    return () => clearTimeout(timer);
  }, [load]);

  async function publish(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api("/portal/announcements", {
        method: "POST",
        body: JSON.stringify({
          title,
          message,
          ticket_no: ticketNo.trim() || null,
          product_id: product ? Number(product) : null,
        }),
      });
      setTitle("");
      setMessage("");
      setTicketNo("");
      setProduct("");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "ประกาศไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  async function resolve(id: number) {
    try {
      await api(`/portal/announcements/${id}/resolve`, { method: "POST" });
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "ปิดประกาศไม่สำเร็จ");
    }
  }

  return (
    <AppShell title="ประกาศสถานะระบบ">
      <div className="page-heading">
        <div>
          <h1>ประกาศสถานะระบบ</h1>
          <p>
            แจ้งลูกค้าในศูนย์ช่วยเหลือเมื่อเกิดเหตุขัดข้องวงกว้าง เพื่อลดเคสซ้ำ
            ถ้าผูกกับเคสหลัก ประกาศจะหายเองเมื่อเคสหลักแก้ไขเสร็จ
          </p>
        </div>
        <a className="button button-secondary" href="/portal/status" target="_blank" rel="noreferrer">
          ดูหน้าที่ลูกค้าเห็น
        </a>
      </div>
      {!allowed ? (
        <section className="surface detail-card">
          <p>เฉพาะผู้ดูแลระบบและหัวหน้าทีมเท่านั้นที่ประกาศสถานะได้</p>
        </section>
      ) : (
        <>
          <section className="surface detail-card">
            <h2>
              <Megaphone size={17} aria-hidden /> ประกาศใหม่
            </h2>
            <form className="grid gap-3" onSubmit={publish}>
              <label className="grid gap-1">
                หัวข้อที่ลูกค้าเห็น *
                <Input required maxLength={255} value={title} onChange={setTitle} placeholder="เช่น ExamPlus เข้าระบบไม่ได้บางส่วน" />
              </label>
              <label className="grid gap-1">
                รายละเอียด *
                <TextArea
                  required
                  maxLength={5000}
                  rows={3}
                  value={message}
                  onValueChange={setMessage}
                  placeholder="กระทบใคร ทำอะไรได้ระหว่างนี้ และคาดว่าจะแจ้งความคืบหน้าเมื่อไร"
                />
              </label>
              <div className="detail-grid">
                <label className="grid gap-1">
                  ผลิตภัณฑ์ที่กระทบ
                  <SelectControl value={product} onValueChange={setProduct} aria-label="ผลิตภัณฑ์ที่กระทบ">
                    <option value="">ไม่ระบุ</option>
                    {products.map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                  </SelectControl>
                </label>
                <label className="grid gap-1">
                  เลขเคสหลัก (Master Incident)
                  <Input value={ticketNo} onChange={setTicketNo} maxLength={32} placeholder="เช่น DVHT-202611-00001" />
                </label>
              </div>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <div>
                <Button type="submit" variant="primary" disabled={busy}>
                  {busy ? "กำลังประกาศ…" : "ประกาศ"}
                </Button>
              </div>
            </form>
          </section>
          <section className="surface detail-card">
            <h2>ประกาศล่าสุด</h2>
            {rows.length === 0 && <p className="text-muted">ยังไม่มีประกาศ</p>}
            <ul className="portal-case-list">
              {rows.map((row) => (
                <li key={row.id} className="portal-case">
                  <span className="portal-case-main">
                    <small>
                      {row.is_active ? "กำลังแสดง" : "ปิดแล้ว"} · {formatDateTime(row.created_at)}
                      {row.product ? ` · ${row.product}` : ""}
                      {row.ticket_no ? ` · เคสหลัก ${row.ticket_no} (${row.status_label})` : ""}
                    </small>
                    <strong>{row.title}</strong>
                    <span>{row.message}</span>
                  </span>
                  {row.is_active && (
                    <Button size="sm" onClick={() => resolve(row.id)}>
                      ปิดประกาศ
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </AppShell>
  );
}
