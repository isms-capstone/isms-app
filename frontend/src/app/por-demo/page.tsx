import { ArrowUpRight, LifeBuoy } from "lucide-react";
import { notFound } from "next/navigation";
import { CompanyMark } from "@/components/layout/sidebar";
import { Button } from "@/components/ui/primitives";

export const dynamic = "force-dynamic";

export default async function ProductDemo() {
  if (process.env.NODE_ENV !== "development") notFound();
  const backend = process.env.BACKEND_URL || "http://127.0.0.1:3000";
  const token = await fetch(new URL("/por-demo", backend), {
    cache: "no-store",
    signal: AbortSignal.timeout(5000),
  })
    .then(async (response) => {
      if (!response.ok) return null;
      return (await response.text()).match(
        /name="token" value="([\w.-]+)"/,
      )?.[1];
    })
    .catch(() => null);

  return (
    <main id="main-content" className="min-h-screen">
      <header className="top-bar flex min-h-14 items-center gap-3 px-5">
        <CompanyMark />
        <div>
          <strong>Deverhood HT</strong>
          <p className="text-muted text-xs">ISMS · Product Support</p>
        </div>
      </header>
      <div className="mx-auto max-w-5xl px-4 py-8 md:px-8">
        <div className="page-heading">
          <div>
            <h1>ผลิตภัณฑ์จำลอง</h1>
            <p>ทดสอบการเปิดเคสจากผลิตภัณฑ์ผ่าน SSO</p>
          </div>
        </div>
        <section className="surface detail-card flex flex-wrap items-center justify-between gap-5">
          <div className="flex items-center gap-3">
            <span className="rounded-lg bg-[var(--soft)] p-3">
              <LifeBuoy size={22} aria-hidden />
            </span>
            <div>
              <h2>ติดต่อทีมสนับสนุน</h2>
              <p className="text-muted">
                เปิดแบบฟอร์มเพื่อส่งรายละเอียดและภาพหน้าจอ
              </p>
            </div>
          </div>
          {token ? (
            <form action="/portal/sso-entry" method="post">
              <input type="hidden" name="token" value={token} />
              <Button type="submit" variant="primary">
                แจ้งปัญหา <ArrowUpRight size={16} aria-hidden />
              </Button>
            </form>
          ) : (
            <p role="alert">เชื่อมต่อผลิตภัณฑ์จำลองไม่ได้</p>
          )}
        </section>
      </div>
    </main>
  );
}
