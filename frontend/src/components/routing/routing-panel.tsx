"use client";
import { useEffect, useState } from "react";
import {
  ArrowUpRight,
  CornerDownLeft,
  UserCheck,
  Clock3,
  GitBranch,
} from "lucide-react";
import { Button, ErrorState, TableSkeleton } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import {
  type RoutingState,
  routingNames,
  routingDate,
  duration,
} from "@/lib/routing-types";
export function RoutingPanel({
  ticketId,
  revision,
  onChanged,
}: {
  ticketId: number;
  revision: string;
  onChanged: () => void;
}) {
  const [state, setState] = useState<RoutingState | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [action, setAction] = useState(""),
    [tier, setTier] = useState(1),
    [recipient, setRecipient] = useState(""),
    [reason, setReason] = useState(""),
    [checked, setChecked] = useState(""),
    [requested, setRequested] = useState(""),
    [retry, setRetry] = useState(0),
    [message, setMessage] = useState("");
  useEffect(() => {
    const c = new AbortController();
    api<RoutingState>(`/tickets/${ticketId}/routing`, { signal: c.signal })
      .then((s) => {
        setState(s);
        setError("");
        setTier(Math.max(0, s.tier - 1));
      })
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    return () => c.abort();
  }, [ticketId, revision, retry]);
  async function send(kind: string) {
    if (!state) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const body: Record<string, unknown> = { expected_version: state.version };
      if (kind === "handoff")
        Object.assign(body, {
          tier,
          assignee_id: Number(recipient),
          reason,
          checked,
          requested,
        });
      if (kind === "assign")
        Object.assign(body, { assignee_id: Number(recipient), reason });
      if (kind === "return")
        Object.assign(body, { event_id: state.return_event_id, reason });
      setState(
        await api<RoutingState>(`/tickets/${ticketId}/${kind}`, {
          method: "POST",
          body: JSON.stringify(body),
        }),
      );
      setAction("");
      setRecipient("");
      setReason("");
      setChecked("");
      setRequested("");
      setMessage("บันทึกการส่งงานแล้ว");
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }
  if (!state)
    return (
      <section className="surface routing-panel">
        {error ? (
          <ErrorState message={error} onRetry={() => setRetry((x) => x + 1)} />
        ) : (
          <TableSkeleton />
        )}
      </section>
    );
  const choices = state.eligible_users.filter(
    (u) => u.default_tier === (action === "handoff" ? tier : state.tier),
  );
  return (
    <section
      className="surface routing-panel"
      aria-label="การส่งต่อและ Routing"
    >
      <div className="routing-heading">
        <div>
          <h2>
            <GitBranch size={18} /> การส่งต่อและ Routing
          </h2>
          <p>
            Tier {state.tier} · ผู้ดูแลการสื่อสารกับลูกค้ายังคงเป็น Owner เดิม
          </p>
        </div>
        <span className="routing-tier">Tier {state.tier}</span>
      </div>
      <dl className="routing-ownership">
        <div>
          <dt>Owner · ดูแลลูกค้า</dt>
          <dd>{state.owner?.name || "ยังไม่ระบุ"}</dd>
        </div>
        <div>
          <dt>Assignee · ผู้ดำเนินการ</dt>
          <dd>{state.assignee?.name || "ยังไม่มีผู้รับผิดชอบ"}</dd>
        </div>
        <div>
          <dt>การตอบสนองครั้งแรก</dt>
          <dd>
            {state.first_response_at
              ? routingDate(state.first_response_at)
              : "ยังไม่ตอบสนอง"}
          </dd>
        </div>
      </dl>
      <div className="routing-actions">
        {state.permissions.self_assign && (
          <Button disabled={busy} onClick={() => send("self-assign")}>
            <UserCheck size={16} />
            รับเคสนี้
          </Button>
        )}
        {state.permissions.respond && (
          <Button disabled={busy} onClick={() => send("respond")}>
            รับทราบและเริ่มตรวจสอบ
          </Button>
        )}
        {state.permissions.handoff && (
          <Button
            onClick={() => {
              setAction("handoff");
              setRecipient("");
            }}
          >
            <ArrowUpRight size={16} />
            ส่งต่อ Tier
          </Button>
        )}
        {state.permissions.return_case && (
          <Button onClick={() => setAction("return")}>
            <CornerDownLeft size={16} />
            ส่งคืนเคส
          </Button>
        )}
        {state.permissions.assign && (
          <Button
            onClick={() => {
              setAction("assign");
              setRecipient("");
            }}
          >
            มอบหมายผู้รับผิดชอบ
          </Button>
        )}
      </div>
      {error && (
        <div role="alert" className="routing-error">
          {error}{" "}
          <Button
            size="sm"
            onClick={() => {
              setAction("");
              setRetry((x) => x + 1);
            }}
          >
            โหลดข้อมูลล่าสุด
          </Button>
        </div>
      )}
      {message && (
        <p role="status" className="routing-success">
          {message}
        </p>
      )}
      {action && (
        <form
          className="routing-form"
          onSubmit={(e) => {
            e.preventDefault();
            void send(action);
          }}
        >
          <h3>{routingNames[action] || "มอบหมายงาน"}</h3>
          {action === "handoff" && (
            <label>
              Tier ปลายทาง
              <select
                value={tier}
                onChange={(e) => {
                  setTier(Number(e.target.value));
                  setRecipient("");
                }}
              >
                {[1, 0]
                  .filter((t) => t < state.tier)
                  .map((t) => (
                    <option key={t} value={t}>
                      Tier {t}
                    </option>
                  ))}
              </select>
            </label>
          )}
          {action !== "return" && (
            <label>
              ผู้รับงาน *
              <select
                required
                value={recipient}
                onChange={(e) => setRecipient(e.target.value)}
              >
                <option value="">
                  เลือกผู้รับงานที่พร้อมและอยู่ในทีมปลายทาง
                </option>
                {choices.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.name} · Tier {u.default_tier}
                  </option>
                ))}
              </select>
              {!choices.length && (
                <small>
                  ไม่มีผู้พร้อมรับงาน กรุณาให้ Admin ตรวจทีมและ Tier
                  ของผลิตภัณฑ์
                </small>
              )}
            </label>
          )}
          <label>
            {action === "return"
              ? "เหตุผล / คำแนะนำในการส่งคืน"
              : "เหตุผลในการส่งงาน"}{" "}
            *
            <textarea
              required
              maxLength={5000}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={3}
            />
          </label>
          {action === "handoff" && (
            <>
              <label>
                สิ่งที่ตรวจสอบไปแล้ว *
                <textarea
                  required
                  maxLength={5000}
                  value={checked}
                  onChange={(e) => setChecked(e.target.value)}
                  rows={3}
                />
              </label>
              <label>
                สิ่งที่ต้องการให้ช่วย *
                <textarea
                  required
                  maxLength={5000}
                  value={requested}
                  onChange={(e) => setRequested(e.target.value)}
                  rows={3}
                />
              </label>
            </>
          )}
          <div className="routing-actions">
            <Button
              type="submit"
              variant="primary"
              disabled={
                busy ||
                !reason.trim() ||
                (action === "handoff" && (!checked.trim() || !requested.trim()))
              }
            >
              {busy ? "กำลังบันทึก..." : "ยืนยันส่งงาน"}
            </Button>
            <Button disabled={busy} onClick={() => setAction("")}>
              ยกเลิก
            </Button>
          </div>
        </form>
      )}
      <div className="routing-times">
        {[2, 1, 0].map((t) => (
          <div key={t}>
            <Clock3 size={16} />
            <span>เวลาใน Tier {t}</span>
            <strong>{duration(state.seconds_by_tier[String(t)] || 0)}</strong>
          </div>
        ))}
      </div>
      <p className="routing-note">
        เวลาสะสมจริงในแต่ละ Tier รวมช่วงรอ ไม่ใช่ SLA ตามเวลาทำการ
        {state.intervals.some((i) => i.is_estimated)
          ? " · ข้อมูลก่อนเปิดใช้ Routing เป็นค่าประมาณจากวันที่สร้างเคส"
          : ""}
      </p>
      <h3>ประวัติการส่งงาน</h3>
      {!state.events.length ? (
        <p className="routing-note">ยังไม่มีการส่งต่อเคส</p>
      ) : (
        <ol className="routing-timeline">
          {[...state.events].reverse().map((event) => (
            <li key={event.id}>
              <div className="routing-event-heading">
                <strong>
                  {routingNames[event.kind] || event.kind} · Tier{" "}
                  {event.from_tier} → {event.to_tier}
                </strong>
                <time>{routingDate(event.created_at)}</time>
              </div>
              <p>
                {event.from_user?.name || "ยังไม่มีผู้รับ"} →{" "}
                {event.to_user?.name || "ยังไม่มีผู้รับ"} · โดย{" "}
                {event.actor?.name || "ระบบอัตโนมัติ"}
              </p>
              <dl>
                <dt>เหตุผล</dt>
                <dd>{event.reason}</dd>
                {event.checked && (
                  <>
                    <dt>ตรวจสอบแล้ว</dt>
                    <dd>{event.checked}</dd>
                  </>
                )}
                {event.requested && (
                  <>
                    <dt>ขอให้ช่วย</dt>
                    <dd>{event.requested}</dd>
                  </>
                )}
              </dl>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
