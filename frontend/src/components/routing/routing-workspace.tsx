"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRightLeft, UserCheck, UsersRound } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import {
  Button,
  Checkbox,
  ErrorState,
  TableSkeleton,
} from "@/components/ui/primitives";
import { api } from "@/lib/api";
import type { RoutingOptions, RoutingUser } from "@/lib/routing-types";
type Workload = RoutingUser & {
  tickets: { id: number; ticket_no: string; subject: string; tier: number }[];
};
export function RoutingWorkspace() {
  const { session, preview, href } = useSession();
  const [me, setMe] = useState<Workload | null>(null),
    [options, setOptions] = useState<RoutingOptions | null>(null),
    [recipient, setRecipient] = useState(""),
    [reason, setReason] = useState(""),
    [error, setError] = useState(""),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!session || preview) return;
    const c = new AbortController();
    Promise.all([
      api<Workload>("/routing/me", { signal: c.signal }),
      api<RoutingOptions>("/routing/options", { signal: c.signal }),
    ])
      .then(([m, o]) => {
        setMe(m);
        setOptions(o);
        setError("");
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, [session, preview, retry]);
  async function availability(value: boolean) {
    const previous = me?.is_available;
    setMe((m) => (m ? { ...m, is_available: value } : m));
    setBusy(true);
    setError("");
    try {
      await api("/routing/me/availability", {
        method: "PUT",
        body: JSON.stringify({ is_available: value }),
      });
      setMe((m) => (m ? { ...m, is_available: value } : m));
      setMessage(
        value
          ? "พร้อมรับงานแล้ว"
          : "ตั้งค่าไม่พร้อมรับงานแล้ว · เคสเดิมยังอยู่จนกว่าจะส่งมอบ",
      );
    } catch (e) {
      setMe((m) =>
        m && previous !== undefined ? { ...m, is_available: previous } : m,
      );
      setError(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }
  async function handover(e: React.FormEvent) {
    e.preventDefault();
    if (!me) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const r = await api<{ count: number }>("/routing/me/handover", {
        method: "POST",
        body: JSON.stringify({
          assignee_id: Number(recipient),
          reason,
          ticket_ids: me.tickets.map((t) => t.id),
        }),
      });
      setMessage(
        `ส่งมอบงานแล้ว ${r.count} เคส โดย Owner เดิมยังดูแลการสื่อสารกับลูกค้า`,
      );
      setRecipient("");
      setReason("");
      setRetry((x) => x + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "ส่งมอบไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }
  return (
    <AppShell title="การส่งมอบงาน">
      <div className="page-heading">
        <div>
          <h1>การส่งมอบงาน</h1>
          <p>จัดการความพร้อมและส่งงานที่กำลังรับผิดชอบให้เพื่อนร่วมทีม</p>
        </div>
      </div>
      {preview ? (
        <section className="surface routing-panel">
          <p>เปิดใช้งานด้วยบัญชีจริงเพื่อจัดการความพร้อมและส่งมอบงาน</p>
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
          {!me || !options ? (
            <TableSkeleton />
          ) : (
            <div className="routing-workspace-grid">
              <section className="surface routing-panel">
                <h2>
                  <UserCheck size={18} /> ความพร้อมรับงาน
                </h2>
                <p>
                  {me.name} · Tier {me.default_tier} ·{" "}
                  {options.teams.find((t) => t.id === me.team_id)?.name ||
                    "ยังไม่มีทีม"}
                </p>
                <Checkbox
                  label="พร้อมรับงานใหม่และงานส่งต่อ"
                  checked={me.is_available}
                  disabled={busy}
                  onChange={(event) => void availability(event.target.checked)}
                />
                <p className="routing-note">
                  เมื่อไม่พร้อมรับงาน ระบบจะไม่เลือกคุณเป็นผู้รับงานใหม่
                  งานที่มีอยู่ยังคงอยู่ในรายการด้านข้าง
                </p>
                {session?.role === "Admin" && (
                  <Link className="text-link" href={href("/routing/admin")}>
                    ตั้งค่าทีมและ Routing →
                  </Link>
                )}
              </section>
              <section className="surface routing-panel">
                <h2>
                  <ArrowRightLeft size={18} /> ส่งมอบงานทั้งหมด{" "}
                  <span className="routing-tier">{me.tickets.length} เคส</span>
                </h2>
                <p>
                  ส่งเฉพาะเคสที่คุณเป็น Assignee และยังเปิดอยู่
                  พร้อมเก็บเหตุผลในประวัติทุกเคส
                </p>
                {me.tickets.length ? (
                  <>
                    <ul className="routing-workload">
                      {me.tickets.map((t) => (
                        <li key={t.id}>
                          <Link href={href(`/cases/${t.id}`)}>
                            <strong>{t.ticket_no}</strong>
                            <span>{t.subject}</span>
                          </Link>
                          <small>Tier {t.tier}</small>
                        </li>
                      ))}
                    </ul>
                    <form className="routing-form" onSubmit={handover}>
                      <label>
                        <UsersRound size={16} /> ผู้รับงานแทน *
                        <select
                          required
                          value={recipient}
                          onChange={(e) => setRecipient(e.target.value)}
                        >
                          <option value="">
                            เลือกเพื่อนร่วมทีมที่พร้อมรับงาน
                          </option>
                          {options.users
                            .filter(
                              (u) =>
                                u.id !== me.id &&
                                u.is_active &&
                                u.is_available &&
                                u.team_id === me.team_id &&
                                me.tickets.every(
                                  (t) => t.tier === u.default_tier,
                                ),
                            )
                            .map((u) => (
                              <option key={u.id} value={u.id}>
                                {u.name} · Tier {u.default_tier}
                              </option>
                            ))}
                        </select>
                      </label>
                      <label>
                        เหตุผลในการส่งมอบ *
                        <textarea
                          required
                          maxLength={5000}
                          rows={3}
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                        />
                      </label>
                      <p className="routing-note">
                        ระบบตรวจทีมตามผลิตภัณฑ์และ Tier ของทุกเคสอีกครั้ง
                        หากมีเคสใดส่งไม่ได้ จะยังไม่ส่งทั้งหมด
                      </p>
                      <Button
                        type="submit"
                        variant="primary"
                        disabled={busy || !reason.trim() || !recipient}
                      >
                        {busy
                          ? "กำลังส่งมอบ..."
                          : `ส่งมอบทั้งหมด ${me.tickets.length} เคส`}
                      </Button>
                    </form>
                  </>
                ) : (
                  <p className="routing-note">ไม่มีเคสที่ต้องส่งมอบ</p>
                )}
              </section>
            </div>
          )}
        </>
      )}
    </AppShell>
  );
}
