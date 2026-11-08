"use client";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import { Button } from "@/components/ui/primitives";
import { api } from "@/lib/api";

export default function PopularTagsPage() {
  const { session } = useSession();
  const [rows, setRows] = useState<{ name: string; ticket_count: number }[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (session?.role !== "Admin") return;
    const controller = new AbortController();
    api<typeof rows>("/categorization/popular-tags?limit=200", { signal: controller.signal })
      .then((result) => { setRows(result); setError(""); })
      .catch((e) => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [session?.role, retry]);
  return <AppShell title="รายงานแท็กยอดนิยม"><section className="surface detail-card popular-tags">
    <h1>แท็กยอดนิยม</h1><p>จำนวนเคสที่ติดแต่ละแท็ก เพื่อพิจารณาสร้างหมวดหมู่ใหม่</p>
    {session?.role !== "Admin" ? <p>รายงานนี้สำหรับผู้ดูแลระบบ</p> : <>
      <Button onClick={() => setRetry((n) => n + 1)}>รีเฟรชรายงาน</Button>
      {loading && <p role="status">กำลังโหลด…</p>}
      {error && <p role="alert" className="form-error">{error}</p>}
      <table><thead><tr><th>แท็ก</th><th>จำนวนเคส</th></tr></thead><tbody>{rows.map((row) => <tr key={row.name}><td>{row.name}</td><td>{row.ticket_count}</td></tr>)}</tbody></table>
      {!loading && !rows.length && !error && <p>ยังไม่มีแท็กในระบบ</p>}
    </>}
  </section></AppShell>;
}
