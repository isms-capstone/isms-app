"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/primitives";

type PortalCase = {
  ticket_no: string;
  subject: string;
  status: string;
  replies: { id: number; body: string }[];
};

export default function ReportPage() {
  const [image, setImage] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [ticket, setTicket] = useState("");
  const [busy, setBusy] = useState(false);

  const [cases, setCases] = useState<PortalCase[]>([]);
  const [status, setStatus] = useState("loading");

  useEffect(() => {
    const controller = new AbortController();
    async function refresh() {
      try {
        const response = await fetch("/api/portal/status", { signal: controller.signal });
        if (!response.ok) {
          setStatus(response.status === 401 ? "expired" : "error");
          return;
        }
        setCases(await response.json());
        setStatus("ready");
      } catch {
        if (!controller.signal.aborted) setStatus("error");
      }
    }
    void refresh();
    const timer = setInterval(refresh, 15000);
    return () => { controller.abort(); clearInterval(timer); };
  }, [ticket]);

  function choose(file: File | null) {
    if (file && (!["image/png", "image/jpeg", "image/webp"].includes(file.type) ||
                 file.size > 10 * 1024 * 1024)) {
      setError("เลือกภาพ PNG, JPEG หรือ WebP ขนาดไม่เกิน 10 MB");
      return;
    }
    setError("");
    setImage(file);
  }

  return (
    <main className="mx-auto max-w-2xl p-6">
      <section className="surface p-6">
        <h1 className="text-xl font-semibold">แจ้งปัญหาจากผลิตภัณฑ์</h1>
        {status === "expired" && <p role="alert">ลิงก์หมดอายุหรือใช้ไม่ได้ กรุณาเปิดใหม่จากผลิตภัณฑ์</p>}
        {status === "error" && <p role="alert">โหลดสถานะไม่สำเร็จ ระบบจะลองใหม่</p>}
        {ticket && <p role="status">รับเรื่องแล้ว หมายเลขเคส {ticket}</p>}
        {!ticket && status === "ready" && (
          <form className="grid gap-4 mt-4" onPaste={(event) => {
            const pasted = [...event.clipboardData.files].find((file) => file.type.startsWith("image/"));
            if (pasted) { event.preventDefault(); choose(pasted); }
          }} onSubmit={async (event) => {
            event.preventDefault();
            if (busy) return;
            const form = new FormData(event.currentTarget);
            if (image) form.set("screenshot", image);
            setBusy(true);
            setError("");
            try {
              const response = await fetch("/api/portal/cases", { method: "POST", body: form });
              const body = await response.json();
              if (response.ok) setTicket(body.ticket_no);
              else setError(typeof body.detail === "string" ? body.detail : "กรุณาตรวจสอบข้อมูล");
            } catch {
              setError("เชื่อมต่อระบบไม่ได้ กรุณาลองอีกครั้ง");
            } finally {
              setBusy(false);
            }
          }}>
            <label className="grid gap-1">หัวข้อ <input className="input" name="subject" required maxLength={255} /></label>
            <label className="grid gap-1">รายละเอียด <textarea className="input" name="description" maxLength={20000} rows={5} /></label>
            <label className="grid gap-1">แนบภาพหน้าจอ หรือวางภาพจากคลิปบอร์ด
              <input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => choose(event.target.files?.[0] ?? null)} />
            </label>
            {image && <p>{image.name} <Button type="button" onClick={() => choose(null)}>ลบภาพ</Button></p>}
            {error && <p role="alert">{error}</p>}
            <Button type="submit" disabled={busy}>ส่งเคส</Button>
          </form>
        )}
        {status === "ready" && cases.length > 0 && (
          <section className="mt-6 grid gap-3" aria-label="เคสและข้อความตอบกลับ">
            <h2 className="font-semibold">เคสและข้อความตอบกลับ</h2>
            {cases.map((item) => (
              <article className="surface p-3" key={item.ticket_no}>
                <h3>{item.ticket_no} · {item.subject}</h3>
                <p>สถานะ: {item.status}</p>
                <ul aria-live="polite">
                  {item.replies.map((reply) => <li className="whitespace-pre-wrap" key={reply.id}>{reply.body}</li>)}
                </ul>
              </article>
            ))}
          </section>
        )}
      </section>
    </main>
  );
}
