"use client";

import { useEffect, useState } from "react";
import { Camera, CheckCircle2, ClipboardList, Paperclip } from "lucide-react";
import { CompanyMark } from "@/components/layout/sidebar";
import { StatusBadge } from "@/components/cases/case-badges";
import { TextArea } from "@/components/ui/company-fields";
import { Button, Input } from "@/components/ui/primitives";

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
        const response = await fetch("/api/portal/status", {
          signal: controller.signal,
        });
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
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [ticket]);

  function choose(file: File | null) {
    if (
      file &&
      (!["image/png", "image/jpeg", "image/webp"].includes(file.type) ||
        file.size > 10 * 1024 * 1024)
    ) {
      setError("เลือกภาพ PNG, JPEG หรือ WebP ขนาดไม่เกิน 10 MB");
      return;
    }
    setError("");
    setImage(file);
  }

  return (
    <main id="main-content" className="min-h-screen">
      <header className="top-bar flex min-h-14 items-center gap-3 px-5">
        <CompanyMark />
        <div>
          <strong>Deverhood HT</strong>
          <p className="text-muted text-xs">ISMS · Product Support</p>
        </div>
      </header>
      <div className="mx-auto max-w-6xl px-4 py-6 md:px-8">
        <div className="page-heading">
          <div>
            <h1>แจ้งปัญหาจากผลิตภัณฑ์</h1>
            <p>ส่งรายละเอียดให้ทีมสนับสนุนและติดตามข้อความตอบกลับ</p>
          </div>
          <a href="/portal" className="button button-secondary">
            ดูเคสทั้งหมดของฉัน
          </a>
        </div>
        <div className="grid items-start gap-5 md:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
          <section className="surface detail-card min-w-0">
            <h2 className="flex items-center gap-2">
              <ClipboardList size={18} aria-hidden /> ข้อมูลเคส
            </h2>
            {status === "loading" && (
              <p role="status" className="text-muted">
                กำลังตรวจสอบสิทธิ์…
              </p>
            )}
            {status === "expired" && (
              <p className="form-error" role="alert">
                ลิงก์หมดอายุหรือใช้ไม่ได้ กรุณาเปิดใหม่จากผลิตภัณฑ์
              </p>
            )}
            {status === "error" && (
              <p className="form-error" role="alert">
                โหลดสถานะไม่สำเร็จ ระบบจะลองใหม่
              </p>
            )}
            {ticket && (
              <p role="status" className="form-message flex items-center gap-2">
                <CheckCircle2 size={18} aria-hidden /> รับเรื่องแล้ว หมายเลขเคส{" "}
                {ticket}
              </p>
            )}
            {!ticket && status === "ready" && (
              <form
                className="grid gap-4 mt-4"
                onPaste={(event) => {
                  const pasted = [...event.clipboardData.files].find((file) =>
                    file.type.startsWith("image/"),
                  );
                  if (pasted) {
                    event.preventDefault();
                    choose(pasted);
                  }
                }}
                onSubmit={async (event) => {
                  event.preventDefault();
                  if (busy) return;
                  const form = new FormData(event.currentTarget);
                  if (image) form.set("screenshot", image);
                  setBusy(true);
                  setError("");
                  try {
                    const response = await fetch("/api/portal/cases", {
                      method: "POST",
                      body: form,
                    });
                    const body = await response.json();
                    if (response.ok) setTicket(body.ticket_no);
                    else
                      setError(
                        typeof body.detail === "string"
                          ? body.detail
                          : "กรุณาตรวจสอบข้อมูล",
                      );
                  } catch {
                    setError("เชื่อมต่อระบบไม่ได้ กรุณาลองอีกครั้ง");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <label className="grid gap-1">
                  หัวข้อ{" "}
                  <Input
                    id="portal-subject"
                    aria-label="หัวข้อ"
                    name="subject"
                    required
                    maxLength={255}
                    placeholder="สรุปปัญหาที่พบ"
                  />
                </label>
                <label className="grid gap-1">
                  รายละเอียด{" "}
                  <TextArea
                    id="portal-description"
                    aria-label="รายละเอียด"
                    name="description"
                    maxLength={20000}
                    rows={5}
                    placeholder="อธิบายสิ่งที่เกิดขึ้น"
                  />
                </label>
                <label className="grid gap-2 rounded-lg border border-[var(--line)] bg-[var(--soft)] p-4">
                  <span className="flex items-center gap-2 font-semibold">
                    <Camera size={17} aria-hidden /> ภาพหน้าจอ
                  </span>
                  <span className="text-muted text-sm">
                    เลือกไฟล์หรือวางภาพจากคลิปบอร์ด · PNG, JPEG, WebP · ไม่เกิน
                    10 MB
                  </span>
                  <input
                    aria-label="แนบภาพหน้าจอ"
                    className="w-full text-sm"
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    onChange={(event) =>
                      choose(event.target.files?.[0] ?? null)
                    }
                  />
                </label>
                {image && (
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex min-w-0 items-center gap-2 break-all">
                      <Paperclip size={16} aria-hidden />
                      {image.name}
                    </span>
                    <Button
                      type="button"
                      onClick={(event) => {
                        const file =
                          event.currentTarget.form?.querySelector<HTMLInputElement>(
                            'input[type="file"]',
                          );
                        if (file) file.value = "";
                        choose(null);
                      }}
                    >
                      ลบภาพ
                    </Button>
                  </div>
                )}
                {error && (
                  <p className="form-error" role="alert">
                    {error}
                  </p>
                )}
                <div className="flex justify-end">
                  <Button type="submit" variant="primary" disabled={busy}>
                    {busy ? "กำลังส่ง…" : "ส่งเคส"}
                  </Button>
                </div>
              </form>
            )}
          </section>
          <section
            className="surface detail-card grid min-w-0 gap-3"
            aria-label="เคสและข้อความตอบกลับ"
          >
            <h2 className="font-semibold">เคสและข้อความตอบกลับ</h2>
            {status === "ready" && cases.length === 0 && (
              <p className="text-muted">ยังไม่มีเคสจากผลิตภัณฑ์นี้</p>
            )}
            {status === "ready" &&
              cases.map((item) => (
                <article className="surface p-3" key={item.ticket_no}>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="text-muted text-sm">{item.ticket_no}</span>
                    <StatusBadge status={item.status} />
                  </div>
                  <h3 className="mt-1 break-words font-semibold">
                    {item.subject}
                  </h3>
                  <ul aria-live="polite">
                    {item.replies.map((reply) => (
                      <li
                        className="mt-2 whitespace-pre-wrap break-words rounded-lg bg-[var(--soft)] p-3"
                        key={reply.id}
                      >
                        {reply.body}
                      </li>
                    ))}
                  </ul>
                </article>
              ))}
          </section>
        </div>
      </div>
    </main>
  );
}
