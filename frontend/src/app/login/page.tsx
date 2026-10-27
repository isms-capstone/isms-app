"use client";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { CompanyMark } from "@/components/layout/sidebar";
import { Button, Input } from "@/components/ui/primitives";
export default function Login() {
  const router = useRouter();
  const [error, setError] = useState(""),
    [saving, setSaving] = useState(false);
  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: form.get("username"),
          password: form.get("password"),
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail);
      router.replace("/my-work");
    } catch (e) {
      setError(e instanceof Error ? e.message : "เข้าสู่ระบบไม่สำเร็จ");
    } finally {
      setSaving(false);
    }
  }
  return (
    <main id="main-content" className="login-screen">
      <div className="login-brand">
        <CompanyMark />
        <span>
          Deverhood HT <small>ISMS · Service Operations</small>
        </span>
      </div>
      <section className="login-card surface">
        <span className="eyebrow">WELCOME TO YOUR WORKSPACE</span>
        <h1>เข้าสู่ระบบ ISMS</h1>
        <p className="text-muted">จัดการเคส ลูกค้า และงานของทีมในที่เดียว</p>
        <form onSubmit={login}>
          <label>
            ชื่อผู้ใช้
            <Input name="username" autoComplete="username" required autoFocus />
          </label>
          <label>
            รหัสผ่าน
            <Input
              name="password"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>
          {error && (
            <p role="alert" className="form-error">
              {error}
            </p>
          )}
          <Button variant="primary" type="submit" disabled={saving}>
            {saving ? "กำลังเข้าสู่ระบบ..." : "เข้าสู่ระบบ"}
          </Button>
        </form>
        <Link className="preview-link" href="/preview/my-work">
          ดู Design Preview ด้วยข้อมูลตัวอย่าง →
        </Link>
      </section>
      <p className="login-caption">
        DEVERHOOD HT · INCIDENT & SERVICE MANAGEMENT
      </p>
    </main>
  );
}
