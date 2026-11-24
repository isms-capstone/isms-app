"use client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Camera, CheckCircle2, Paperclip } from "lucide-react";
import { PortalShell, portalApi, usePortalMe } from "@/components/portal/portal-shell";
import { SelectControl, TextArea } from "@/components/ui/company-fields";
import { Button, Input } from "@/components/ui/primitives";

const IMAGE_TYPES = ["image/png", "image/jpeg", "image/webp"];

export default function PortalNewCase() {
  const me = usePortalMe();
  const [system, setSystem] = useState(""),
    [image, setImage] = useState<File | null>(null),
    [error, setError] = useState(""),
    [created, setCreated] = useState(""),
    [busy, setBusy] = useState(false);
  const selected = system || (me?.systems.length === 1 ? String(me.systems[0].id) : "");

  function choose(file: File | null) {
    if (file && (!IMAGE_TYPES.includes(file.type) || file.size > 10 * 1024 * 1024)) {
      setError("เลือกภาพ PNG, JPEG หรือ WebP ขนาดไม่เกิน 10 MB");
      return;
    }
    setError("");
    setImage(file);
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const form = new FormData(event.currentTarget);
    form.set("product_instance_id", selected);
    form.delete("screenshot-input");
    if (image) form.set("screenshot", image);
    setBusy(true);
    setError("");
    try {
      const result = await portalApi<{ ticket_no: string }>("me/cases", { method: "POST", body: form });
      setCreated(result.ticket_no);
    } catch (e) {
      setError(e instanceof Error ? e.message : "ส่งเรื่องไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PortalShell me={me}>
      <div className="page-heading">
        <div>
          <h1>แจ้งปัญหาใหม่</h1>
          <p>บอกเราว่าเกิดอะไรขึ้น ทีมสนับสนุนจะติดต่อกลับตามลำดับความเร่งด่วน</p>
        </div>
      </div>
      <section className="surface detail-card portal-form">
        {created ? (
          <div className="grid gap-3" role="status">
            <p className="form-message">
              <CheckCircle2 size={18} aria-hidden /> รับเรื่องแล้ว หมายเลขเคส <strong>{created}</strong>
            </p>
            <p className="text-muted">ติดตามสถานะและข้อความตอบกลับได้ที่หน้าเคสของคุณ และทางอีเมล</p>
            <Link href={`/portal/cases/${created}`} className="button button-primary">
              ดูเคสนี้
            </Link>
          </div>
        ) : (
          <form
            className="grid gap-4"
            onSubmit={submit}
            onPaste={(event) => {
              const pasted = [...event.clipboardData.files].find((file) => file.type.startsWith("image/"));
              if (pasted) {
                event.preventDefault();
                choose(pasted);
              }
            }}
          >
            <label className="grid gap-1">
              ระบบที่พบปัญหา *
              <SelectControl
                aria-label="ระบบที่พบปัญหา"
                value={selected}
                onValueChange={setSystem}
                required
                disabled={!me?.systems.length}
              >
                <option value="">เลือกระบบ</option>
                {me?.systems.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name.startsWith(item.product) ? item.name : `${item.product} · ${item.name}`}
                  </option>
                ))}
              </SelectControl>
              {me && !me.systems.length && (
                <span className="field-hint">องค์กรของคุณยังไม่มีระบบที่ลงทะเบียนไว้ กรุณาติดต่อทีมสนับสนุน</span>
              )}
            </label>
            <label className="grid gap-1">
              หัวข้อ *
              <Input name="subject" required maxLength={255} placeholder="สรุปปัญหาสั้น ๆ เช่น นักศึกษาส่งคำตอบไม่ได้" />
            </label>
            <label className="grid gap-1">
              รายละเอียด
              <TextArea
                name="description"
                maxLength={20000}
                rows={5}
                placeholder="เกิดขึ้นเมื่อไร กับใคร ทำขั้นตอนไหนแล้วพบปัญหา มีข้อความแจ้งเตือนอะไร"
              />
            </label>
            <label className="grid gap-2 portal-dropzone">
              <span className="flex items-center gap-2 font-semibold">
                <Camera size={17} aria-hidden /> ภาพหน้าจอ (ไม่บังคับ)
              </span>
              <span className="text-muted text-sm">เลือกไฟล์ หรือวางภาพ (Ctrl/⌘+V) · PNG, JPEG, WebP ไม่เกิน 10 MB</span>
              <input
                name="screenshot-input"
                aria-label="แนบภาพหน้าจอ"
                type="file"
                accept={IMAGE_TYPES.join(",")}
                onChange={(event) => choose(event.target.files?.[0] ?? null)}
              />
            </label>
            {image && (
              <p className="flex items-center gap-2 break-all">
                <Paperclip size={16} aria-hidden /> {image.name}
                <Button type="button" size="sm" onClick={() => choose(null)}>
                  เอาออก
                </Button>
              </p>
            )}
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <div className="flex justify-end">
              <Button type="submit" variant="primary" disabled={busy || !selected}>
                {busy ? "กำลังส่ง…" : "ส่งเรื่อง"}
              </Button>
            </div>
          </form>
        )}
      </section>
    </PortalShell>
  );
}
