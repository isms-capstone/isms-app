"use client";
import { useEffect, useState } from "react";
import { GitBranch, Clock3, UsersRound, ShieldCheck } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import {
  Button,
  Checkbox,
  Input,
  ErrorState,
  TableSkeleton,
} from "@/components/ui/primitives";
import { api } from "@/lib/api";
import type { RoutingOptions } from "@/lib/routing-types";
type Config = {
  policy: {
    s1_minutes: number;
    enabled: boolean;
    business_calendar_id: number | null;
  };
  leaders: { team_id: number; leader_id: number }[];
  worker: { last_success_at: string | null } | null;
};
export function RoutingAdmin() {
  const { session, preview } = useSession();
  const [options, setOptions] = useState<RoutingOptions | null>(null),
    [config, setConfig] = useState<Config | null>(null),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!session || session.role !== "Admin" || preview) return;
    const c = new AbortController();
    Promise.all([
      api<RoutingOptions>("/routing/options", { signal: c.signal }),
      api<Config>("/routing/config", { signal: c.signal }),
    ])
      .then(([o, s]) => {
        setOptions(o);
        setConfig(s);
        setError("");
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, [session, preview, retry]);
  async function save(path: string, body: unknown) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await api(path, { method: "PUT", body: JSON.stringify(body) });
      setMessage("บันทึกการตั้งค่าแล้ว");
      setRetry((x) => x + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }
  function form(e: React.FormEvent<HTMLFormElement>, kind: string) {
    e.preventDefault();
    const f = new FormData(e.currentTarget),
      n = (key: string) => Number(f.get(key));
    if (kind === "route")
      void save("/routing/routes", {
        product_id: n("product"),
        tier: n("tier"),
        team_id: n("team"),
      });
    if (kind === "leader")
      void save(`/routing/teams/${n("team")}/leader`, { leader_id: n("user") });
    if (kind === "tier")
      void save(`/routing/users/${n("user")}/tier`, {
        default_tier: n("tier"),
      });
  }
  const select = (
    name: string,
    label: string,
    rows: { id: number; name: string }[],
  ) => (
    <label>
      {label}
      <select required name={name} defaultValue="">
        <option value="">เลือก{label}</option>
        {rows.map((r) => (
          <option key={r.id} value={r.id}>
            {r.name}
          </option>
        ))}
      </select>
    </label>
  );
  const tiers = (
    <label>
      Tier
      <select name="tier" defaultValue="2">
        {[2, 1, 0].map((t) => (
          <option key={t} value={t}>
            Tier {t}
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <AppShell title="ตั้งค่า Escalation & Routing">
      <div className="page-heading">
        <div>
          <h1>Escalation & Routing</h1>
          <p>ตั้งทีมปลายทาง ผู้รับผิดชอบ และเงื่อนไขส่งต่อเคส</p>
        </div>
      </div>
      {preview || session?.role !== "Admin" ? (
        <section className="surface routing-panel">
          <h2>
            <ShieldCheck size={18} /> สำหรับผู้ดูแลระบบ
          </h2>
          <p>ใช้บัญชี Admin เพื่อปรับการตั้งค่า Routing</p>
        </section>
      ) : (
        <>
          {error && (
            <ErrorState
              message={error}
              onRetry={() => setRetry((x) => x + 1)}
            />
          )}{" "}
          {message && (
            <p role="status" className="routing-success">
              {message}
            </p>
          )}
          {!options || !config ? (
            <TableSkeleton />
          ) : (
            <>
              <div className="routing-admin-grid">
                <section className="surface routing-panel">
                  <h2>
                    <GitBranch size={18} /> ทีมตามผลิตภัณฑ์และ Tier
                  </h2>
                  <p>
                    เส้นทางที่กำหนดที่นี่มีลำดับก่อน Automation Rules
                    และทีมเริ่มต้นของผลิตภัณฑ์
                  </p>
                  <form
                    className="routing-form"
                    onSubmit={(e) => form(e, "route")}
                  >
                    {select("product", "ผลิตภัณฑ์", options.products)}
                    {tiers}
                    {select("team", "ทีมปลายทาง", options.teams)}
                    <Button type="submit" variant="primary" disabled={busy}>
                      บันทึกเส้นทาง
                    </Button>
                  </form>
                </section>
                <section className="surface routing-panel">
                  <h2>
                    <UsersRound size={18} /> หัวหน้าทีม
                  </h2>
                  <p>รับการแจ้งเตือนเคส NEW ค้างและเคส S1 ที่ไม่มีการตอบสนอง</p>
                  <form
                    className="routing-form"
                    onSubmit={(e) => form(e, "leader")}
                  >
                    {select("team", "ทีม", options.teams)}
                    {select(
                      "user",
                      "หัวหน้าทีม",
                      options.users.filter((u) => u.is_active),
                    )}
                    <small>ต้องเป็นสมาชิกที่เปิดใช้งานอยู่ในทีมที่เลือก</small>
                    <Button type="submit" variant="primary" disabled={busy}>
                      บันทึกหัวหน้าทีม
                    </Button>
                  </form>
                </section>
                <section className="surface routing-panel">
                  <h2>
                    <ShieldCheck size={18} /> Tier เริ่มต้นของผู้ใช้
                  </h2>
                  <p>Tier 2 สนับสนุน · Tier 1 ผู้เชี่ยวชาญ · Tier 0 ทีมพัฒนา</p>
                  <form
                    className="routing-form"
                    onSubmit={(e) => form(e, "tier")}
                  >
                    {select("user", "ผู้ใช้", options.users)}
                    {tiers}
                    <Button type="submit" variant="primary" disabled={busy}>
                      บันทึก Tier
                    </Button>
                  </form>
                </section>
                <section className="surface routing-panel">
                  <h2>
                    <Clock3 size={18} /> การส่งต่อ S1 อัตโนมัติ
                  </h2>
                  <form
                    className="routing-form"
                    onSubmit={(e) => {
                      e.preventDefault();
                      void save("/routing/policy", config.policy);
                    }}
                  >
                    <Checkbox
                      label="เปิดใช้การส่งต่อ S1 เมื่อไม่มีการตอบสนอง"
                      checked={config.policy.enabled}
                      onChange={(value) =>
                        setConfig({
                          ...config,
                          policy: {
                            ...config.policy,
                            enabled: value.target.checked,
                          },
                        })
                      }
                    />
                    <label>
                      ไม่มีการตอบสนองเกิน (นาที)
                      <Input
                        aria-label="S1 timeout minutes"
                        type="number"
                        min={1}
                        max={1440}
                        required
                        value={String(config.policy.s1_minutes)}
                        onChange={(value) =>
                          setConfig({
                            ...config,
                            policy: {
                              ...config.policy,
                              s1_minutes: Number(value),
                            },
                          })
                        }
                      />
                    </label>
                    <label>
                      ปฏิทินแจ้งเตือน NEW ค้าง
                      <select
                        value={config.policy.business_calendar_id || ""}
                        onChange={(e) =>
                          setConfig({
                            ...config,
                            policy: {
                              ...config.policy,
                              business_calendar_id: e.target.value
                                ? Number(e.target.value)
                                : null,
                            },
                          })
                        }
                      >
                        <option value="">
                          จันทร์–ศุกร์ 08:00–17:00 น. (ไทย)
                        </option>
                        {options.calendars.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <p className="routing-note">
                      ตรวจทุก 5 นาที · NEW เกิน 15 นาทีแจ้งเฉพาะเวลาทำการ · S1
                      ตรวจตลอดเวลา
                    </p>
                    <Button type="submit" variant="primary" disabled={busy}>
                      บันทึกนโยบาย
                    </Button>
                  </form>
                </section>
              </div>
              <section className="surface routing-panel">
                <h2>การตั้งค่าปัจจุบัน</h2>
                <div className="routing-config-list">
                  {options.routes.length ? (
                    options.routes.map((r) => (
                      <p key={`${r.product_id}:${r.tier}`}>
                        <strong>
                          {options.products.find((p) => p.id === r.product_id)
                            ?.name || r.product_id}
                        </strong>
                        <span>
                          Tier {r.tier} →{" "}
                          {options.teams.find((t) => t.id === r.team_id)
                            ?.name || r.team_id}
                        </span>
                      </p>
                    ))
                  ) : (
                    <p>ยังไม่ได้ระบุทีมตามผลิตภัณฑ์ / Tier</p>
                  )}
                  {config.leaders.map((r) => (
                    <p key={r.team_id}>
                      <strong>
                        {options.teams.find((t) => t.id === r.team_id)?.name}
                      </strong>
                      <span>
                        หัวหน้าทีม:{" "}
                        {options.users.find((u) => u.id === r.leader_id)?.name}
                      </span>
                    </p>
                  ))}
                  {options.users.map((u) => (
                    <p key={`user:${u.id}`}>
                      <strong>{u.name}</strong>
                      <span>
                        Tier {u.default_tier} ·{" "}
                        {u.is_available ? "พร้อมรับงาน" : "ไม่พร้อมรับงาน"}
                      </span>
                    </p>
                  ))}
                </div>
                <p className="routing-note">
                  Worker ตรวจครั้งล่าสุด:{" "}
                  {config.worker?.last_success_at ||
                    "ยังไม่พบการทำงาน — ต้องเปิด routing-worker"}
                </p>
              </section>
            </>
          )}
        </>
      )}
    </AppShell>
  );
}
