"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, CheckCircle2, Clock3 } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import {
  Button,
  ErrorState,
  Input,
  TableSkeleton,
} from "@/components/ui/primitives";
import { api } from "@/lib/api";
import type { Ticket, Organization } from "@/lib/types";
import { channelNames, statusNames } from "@/lib/types";
import { previewData } from "@/lib/preview";
import { PriorityBadge, ChannelLabel } from "./case-badges";
export function CaseDetail({ id }: { id: number }) {
  const { session, preview, href } = useSession();
  const [ticket, setTicket] = useState<Ticket | null>(
      preview
        ? [...previewData.rows, ...previewData.drafts].find(
            (row) => row.id === id,
          ) || null
        : null,
    ),
    [customer, setCustomer] = useState(""),
    [error, setError] = useState(""),
    [field, setField] = useState("subject"),
    [value, setValue] = useState(""),
    [reported, setReported] = useState(""),
    [saving, setSaving] = useState(false),
    [message, setMessage] = useState(""),
    [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (preview || !session) return;
    const controller = new AbortController();
    api<Ticket>(`/tickets/${id}`, { signal: controller.signal })
      .then(async (row) => {
        if (row.organization_id) {
          const org = await api<Organization>(
            `/customers/organizations/${row.organization_id}`,
            { signal: controller.signal },
          );
          setCustomer(org.name);
        }
        setTicket(row);
        setValue(row.subject || "");
        setReported(localDateTime(row.reported_at));
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [preview, session, id, attempt]);
  async function save(path: string, body: unknown) {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const updated = await api<Ticket>(`/tickets/${id}/${path}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setTicket(updated);
      setMessage("บันทึกข้อมูลแล้ว");
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");
    } finally {
      setSaving(false);
    }
  }
  const editable = !preview && session?.can_create_cases;
  return (
    <AppShell title="รายละเอียดเคส">
      <div className="page-heading">
        <div>
          <Link
            className="text-link inline-flex items-center gap-1 mb-3"
            href={href("/my-work")}
          >
            <ArrowLeft size={13} />
            กลับงานของฉัน
          </Link>
          <h1>{ticket?.ticket_no || "รายละเอียดเคสร่าง"}</h1>
          <p>{ticket?.subject || "รายละเอียดเคส"}</p>
        </div>
        {ticket && (
          <span className={`status-label status-${ticket.status}`}>
            {statusNames[ticket.status] || ticket.status}
          </span>
        )}
      </div>
      {error && (
        <ErrorState message={error} onRetry={() => setAttempt((n) => n + 1)} />
      )}{" "}
      {!ticket ? (
        !error && <TableSkeleton />
      ) : (
        <section className="surface detail-card">
          <h2>ข้อมูลเคส</h2>
          <dl className="detail-grid">
            {[
              [
                "ลูกค้า",
                preview
                  ? previewData.rows.find((row) => row.id === id)?.customer ||
                    "TU · คณะแพทยศาสตร์"
                  : customer || "ยังไม่ระบุ",
              ],
              ["สถานะ", statusNames[ticket.status] || ticket.status],
              [
                "เวลาที่ลูกค้าแจ้ง",
                new Date(ticket.reported_at).toLocaleString("th-TH"),
              ],
              [
                "เวลาที่ระบบสร้าง",
                new Date(ticket.created_at).toLocaleString("th-TH"),
              ],
              ["รายละเอียด", ticket.description || "ยังไม่มีรายละเอียด"],
            ].map(([label, text]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{text}</dd>
              </div>
            ))}
            <div>
              <dt>ช่องทาง</dt>
              <dd>
                <ChannelLabel channel={ticket.channel} />
              </dd>
            </div>
            <div>
              <dt>Priority</dt>
              <dd>
                <PriorityBadge value={ticket.severity} />
              </dd>
            </div>
            <div>
              <dt>SLA</dt>
              <dd className="text-muted">ยังไม่มีการคำนวณจาก Backend</dd>
            </div>
          </dl>
          {editable &&
            ticket.status === "DRAFT" &&
            ticket.created_by_id === session?.id && (
              <form
                className="detail-edit"
                onSubmit={(e) => {
                  e.preventDefault();
                  save("draft-field", { field, value: value || null });
                }}
              >
                <h3>เติมข้อมูลร่างทีละช่อง</h3>
                <label>
                  ช่องที่ต้องการแก้ไข
                  <select
                    className="input"
                    value={field}
                    onChange={(e) => {
                      const next = e.target.value;
                      setField(next);
                      setValue(
                        String(
                          ticket[
                            next as "subject" | "description" | "channel"
                          ] || "",
                        ),
                      );
                    }}
                  >
                    <option value="subject">หัวข้อ</option>
                    <option value="description">รายละเอียด</option>
                    <option value="channel">ช่องทาง</option>
                  </select>
                </label>
                <label>
                  ข้อมูล
                  {field === "channel" ? (
                    <select
                      className="input"
                      value={value}
                      onChange={(e) => setValue(e.target.value)}
                    >
                      <option value="">ยังไม่ระบุ</option>
                      {Object.entries(channelNames).map(([id, label]) => (
                        <option key={id} value={id}>
                          {label}
                        </option>
                      ))}
                    </select>
                  ) : field === "description" ? (
                    <textarea
                      maxLength={20000}
                      value={value}
                      onChange={(e) => setValue(e.target.value)}
                    />
                  ) : (
                    <Input maxLength={255} value={value} onChange={setValue} />
                  )}
                </label>
                <div>
                  <Button variant="primary" type="submit" disabled={saving}>
                    บันทึกช่องนี้
                  </Button>
                  <span className="text-muted text-xs">
                    เคสยังคงเป็น Draft หลังบันทึก
                  </span>
                </div>
              </form>
            )}
          {editable &&
            (session?.role === "Admin" ||
              [
                ticket.created_by_id,
                ticket.owner_id,
                ticket.assignee_id,
              ].includes(session?.id ?? -1)) && (
              <form
                className="detail-edit"
                onSubmit={(e) => {
                  e.preventDefault();
                  if (reported)
                    save("reported-at", {
                      reported_at: new Date(reported).toISOString(),
                    });
                }}
              >
                <h3 className="flex items-center gap-2">
                  <Clock3 size={14} />
                  เวลาที่ลูกค้าแจ้ง
                </h3>
                <label>
                  แก้เวลารับแจ้ง (ย้อนหลังได้ไม่เกิน 7 วัน)
                  <Input
                    type="datetime-local"
                    value={reported}
                    required
                    onChange={setReported}
                  />
                </label>
                <div>
                  <Button type="submit" disabled={saving}>
                    บันทึกเวลารับแจ้ง
                  </Button>
                </div>
              </form>
            )}
          {message && (
            <p role="status" className="form-message flex items-center gap-2">
              <CheckCircle2 size={15} />
              {message}
            </p>
          )}
        </section>
      )}
    </AppShell>
  );
}
function localDateTime(value: string) {
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}
