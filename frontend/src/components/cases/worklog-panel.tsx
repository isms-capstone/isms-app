"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { channelNames, type Ticket } from "@/lib/types";
import { Button } from "@/components/ui/primitives";
import { useSession } from "@/components/providers/session-provider";
import type { WorklogRecord } from "@/lib/worklog-contract";

type TimelineEvent = {
  id: string;
  kind: string;
  body: string;
  actor: string | null;
  created_at: string;
  channel?: string | null;
  changes?: Record<string, unknown>;
  details?: Record<string, unknown>;
};
const labels: Record<string, string> = {
  internal_note: "Internal Note",
  public_reply: "Public Reply",
  case_created: "สร้างเคส",
  status_changed: "เปลี่ยนสถานะ",
  categorization_updated: "เปลี่ยนหมวดหมู่",
  categorization_created: "จัดหมวดหมู่",
  attachment: "แนบไฟล์",
  request_start: "เริ่มดำเนินคำขอ",
  request_fulfil: "ส่งมอบผลคำขอ",
  request_confirm: "ยืนยันและปิดคำขอ",
  similarity_decision: "ตัดสินใจจากเคสที่คล้ายกัน",
};
const fieldLabels: Record<string, string> = {
  module_id: "โมดูล",
  category_id: "ประเภทปัญหา",
  symptom_id: "อาการ",
  service_stage_id: "ช่วงเวลาสอบ",
  ticket_type_id: "ประเภทเคส",
  product_instance_id: "ระบบที่ลูกค้าใช้งาน",
  impact_scope: "ขอบเขตผลกระทบ",
  is_exam_window: "ระหว่างสอบจริง",
  severity: "Severity",
  severity_overridden_reason: "เหตุผลปรับ Severity",
  root_cause_code_id: "รหัสสาเหตุ",
  root_cause_detail: "คำอธิบายสาเหตุ",
  resolution_code_id: "รหัสวิธีแก้",
  resolution_detail: "คำอธิบายวิธีแก้",
  tags: "แท็ก",
  action: "ขั้นตอนคำขอ",
  status: "สถานะ",
  feedback_id: "ผลการค้นหา",
  chosen_ticket_id: "เคสต้นทาง",
  decision: "แนวทางที่เลือก",
};
export function WorklogPanel({ ticket }: { ticket: Ticket }) {
  const { session } = useSession();
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [kind, setKind] = useState("internal_note");
  const [body, setBody] = useState("");
  const [channel, setChannel] = useState("");
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [loading, setLoading] = useState(true);
  const [source, setSource] = useState("");
  const [loadedCount, setLoadedCount] = useState(0);
  const editable =
    session?.can_create_cases &&
    (session.role === "Admin" ||
      [ticket.created_by_id, ticket.owner_id, ticket.assignee_id].includes(
        session.id,
      ));
  const loadMore = useCallback(async () => {
    setLoading(true);
    try {
      const result = await api<{ items: TimelineEvent[]; total: number }>(
        `/tickets/${ticket.id}/timeline?offset=${loadedCount}`,
      );
      setLoadedCount((previous) => previous + result.items.length);
      setEvents((previous) => mergeEvents(previous, result.items));
      setTotal(result.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "โหลดไม่สำเร็จ");
    } finally {
      setLoading(false);
    }
  }, [ticket.id, loadedCount]);
  useEffect(() => {
    const controller = new AbortController();
    api<{ items: TimelineEvent[]; total: number; source?: string }>(
      `/tickets/${ticket.id}/timeline`,
      { signal: controller.signal },
    )
      .then((result) => {
        setEvents(result.items);
        setLoadedCount(result.items.length);
        setTotal(result.total);
        setSource(result.source || "unified");
        setError("");
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [ticket, refresh]);
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const saved = await api<WorklogRecord>(`/tickets/${ticket.id}/worklogs`, {
        method: "POST",
        body: JSON.stringify({
          kind,
          body,
          channel: kind === "public_reply" ? channel : null,
        }),
      });
      setEvents((previous) =>
        mergeEvents(previous, [{ ...saved, id: `worklog-${saved.id}` }]),
      );
      setTotal((previous) => previous + 1);
      setFilter("all");
      setBody("");
      setMessage("บันทึกข้อความแล้ว");
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="surface detail-card worklog-panel">
      <div className="timeline-heading">
        <h2>ไทม์ไลน์รวม</h2>
        <label>
          แสดง
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="all">ทั้งหมด</option>
            <option value="internal_note">Internal Note</option>
            <option value="public_reply">Public Reply</option>
            <option value="categorization_updated">ประวัติหมวดหมู่</option>
          </select>
        </label>
      </div>
      {source === "worklogs" && (
        <p className="field-hint">
          แสดงประวัติการสื่อสาร · ประวัติการเปลี่ยนสถานะยังไม่พร้อมใช้งาน
        </p>
      )}
      <ol className="worklog-timeline">
        {events
          .filter((event) => filter === "all" || event.kind === filter)
          .map((event) => (
            <li key={event.id} className={`timeline-event ${event.kind}`}>
              <div className="timeline-event-heading">
                <strong>{labels[event.kind] || event.kind}</strong>
                <span>{event.actor || "ระบบ"}</span>
                <time dateTime={event.created_at}>
                  {new Date(event.created_at).toLocaleString("th-TH")}
                </time>
              </div>
              {event.channel && (
                <span className="delivery-channel">
                  ส่งจริงผ่าน {channelNames[event.channel] || event.channel}
                </span>
              )}
              <p>{event.body}</p>
              {event.changes && (
                <details>
                  <summary>ค่าเดิม / ค่าใหม่</summary>
                  <dl>
                    {Object.entries(event.changes).map(([key, change]) => {
                      const pair = change as { old: unknown; new: unknown };
                      return (
                        <div key={key}>
                          <dt>{fieldLabels[key] || key}</dt>
                          <dd>
                            {pair &&
                            typeof pair === "object" &&
                            "new" in pair ? (
                              <>
                                {JSON.stringify(pair.old ?? null)} →{" "}
                                {JSON.stringify(pair.new ?? null)}
                              </>
                            ) : (
                              JSON.stringify(change)
                            )}
                          </dd>
                        </div>
                      );
                    })}
                  </dl>
                </details>
              )}
            </li>
          ))}
      </ol>
      {!loading && events.length === 0 && <p>ยังไม่มีบันทึก</p>}
      {loading && <p role="status">กำลังโหลดไทม์ไลน์…</p>}
      {events.length < total && (
        <Button onClick={loadMore} disabled={loading}>
          โหลดเหตุการณ์เพิ่มเติม
        </Button>
      )}
      {editable && (
        <form className="worklog-composer" onSubmit={submit}>
          <div className="worklog-tabs" role="group" aria-label="ประเภทข้อความ">
            <Button
              aria-pressed={kind === "internal_note"}
              onClick={() => {
                setKind("internal_note");
                setChannel("");
              }}
            >
              Internal Note
            </Button>
            <Button
              aria-pressed={kind === "public_reply"}
              onClick={() => setKind("public_reply")}
            >
              Public Reply
            </Button>
          </div>
          <p className="field-hint">
            {kind === "internal_note"
              ? "บันทึกภายในทีม"
              : "บันทึกข้อความที่ส่งให้ลูกค้าแล้ว พร้อมช่องทางที่ใช้จริง"}
          </p>
          {kind === "public_reply" && (
            <label>
              ช่องทางที่ส่งจริง *
              <select
                aria-label="ช่องทางที่ส่งจริง *"
                required
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
              >
                <option value="">เลือกช่องทางที่ส่งจริง</option>
                {Object.entries(channelNames).map(([key, name]) => (
                  <option key={key} value={key}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label>
            ข้อความ *
            <textarea
              aria-label="ข้อความ *"
              required
              maxLength={20000}
              rows={4}
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
          </label>
          <Button
            type="submit"
            variant="primary"
            disabled={busy || loading || !body.trim()}
          >
            {busy ? "กำลังบันทึก…" : "บันทึกข้อความ"}
          </Button>
        </form>
      )}
      {error && (
        <p role="alert" className="form-error">
          {error}{" "}
          <button type="button" onClick={() => setRefresh((n) => n + 1)}>
            โหลดไทม์ไลน์อีกครั้ง
          </button>
        </p>
      )}
      {message && (
        <p role="status" className="form-message">
          {message}
        </p>
      )}
    </section>
  );
}

function mergeEvents(previous: TimelineEvent[], incoming: TimelineEvent[]) {
  const events = new Map(previous.map((event) => [event.id, event]));
  incoming.forEach((event) => events.set(event.id, event));
  return [...events.values()].sort(
    (a, b) =>
      a.created_at.localeCompare(b.created_at) ||
      a.id.localeCompare(b.id, undefined, { numeric: true }),
  );
}
