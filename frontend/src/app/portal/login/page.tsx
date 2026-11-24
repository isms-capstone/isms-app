"use client";
import { Suspense, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { Mail, LogIn } from "lucide-react";
import { PortalShell } from "@/components/portal/portal-shell";
import { Button, Input } from "@/components/ui/primitives";

function PortalLoginForm() {
  const params = useSearchParams();
  const token = params.get("token");
  const [email, setEmail] = useState(""),
    [sent, setSent] = useState(""),
    [devLinks, setDevLinks] = useState<string[]>([]),
    [error, setError] = useState(params.get("error") ? "ลิงก์หมดอายุหรือถูกใช้ไปแล้ว กรุณาขอลิงก์ใหม่" : ""),
    [busy, setBusy] = useState(false);

  async function request(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/portal/auth/link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "ส่งลิงก์ไม่สำเร็จ");
      setSent(data.message);
      setDevLinks(data.dev_links || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "ส่งลิงก์ไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  return (
    <PortalShell public>
      <section className="surface detail-card portal-login">
        {token ? (
          <form method="post" action="/portal/login/verify" className="grid gap-4">
            <h1>ยืนยันการเข้าสู่ระบบ</h1>
            <p className="text-muted">กดปุ่มด้านล่างเพื่อเข้าดูเคสของคุณ ลิงก์นี้ใช้ได้ครั้งเดียว</p>
            <input type="hidden" name="token" value={token} />
            <Button type="submit" variant="primary">
              <LogIn size={16} aria-hidden /> เข้าสู่ระบบ
            </Button>
          </form>
        ) : (
          <form onSubmit={request} className="grid gap-4">
            <h1>ติดตามเคสของคุณ</h1>
            <p className="text-muted">
              กรอกอีเมลที่ใช้ติดต่อทีมสนับสนุน เราจะส่งลิงก์เข้าสู่ระบบให้ทางอีเมล
              ไม่ต้องตั้งรหัสผ่าน
            </p>
            <label className="grid gap-1">
              อีเมล
              <Input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={setEmail}
                placeholder="name@organization.ac.th"
              />
            </label>
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            {sent ? (
              <p className="form-message flex items-center gap-2" role="status">
                <Mail size={16} aria-hidden /> {sent}
              </p>
            ) : null}
            {devLinks.length > 0 && (
              <p className="field-hint">
                โหมดพัฒนา (ยังไม่ได้ตั้งค่าอีเมล):{" "}
                {devLinks.map((link) => (
                  <a key={link} href={new URL(link).pathname + new URL(link).search} className="text-link">
                    เปิดลิงก์เข้าสู่ระบบ
                  </a>
                ))}
              </p>
            )}
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "กำลังส่ง…" : "ส่งลิงก์เข้าสู่ระบบ"}
            </Button>
            <p className="field-hint">
              ใช้งานผลิตภัณฑ์ของ Deverhood อยู่? กดปุ่ม &quot;แจ้งปัญหา&quot; ในผลิตภัณฑ์ได้เลยโดยไม่ต้องเข้าสู่ระบบ
            </p>
          </form>
        )}
      </section>
    </PortalShell>
  );
}

export default function PortalLogin() {
  return (
    <Suspense fallback={null}>
      <PortalLoginForm />
    </Suspense>
  );
}
