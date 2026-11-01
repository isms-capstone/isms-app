"use client";
import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { ArrowLeft, Clock3, CheckCircle2, Pencil, X } from "lucide-react";
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
import { LifecycleActions } from "./lifecycle-actions";
import { PriorityBadge, ChannelLabel, StatusBadge } from "./case-badges";

// แถวประวัติ (audit log) จาก GET /tickets/{id}/history
type HistoryRow = {
  id: number;
  actor_id: number;
  actor_name: string;
  from_status: string | null;
  to_status: string;
  created_at: string;
  details: Record<string, unknown>;
  owner_name: string | null;
};

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
    [attempt, setAttempt] = useState(0),
    [assigneeName, setAssigneeName] = useState("ยังไม่มีผู้รับผิดชอบ"),
    [creatorName, setCreatorName] = useState("–"),
    [history, setHistory] = useState<HistoryRow[]>([]),
    [editingNew, setEditingNew] = useState(false),
    [newSubject, setNewSubject] = useState(""),
    [newDescription, setNewDescription] = useState(""),
    [newChannel, setNewChannel] = useState(""),
    [newDetails, setNewDetails] = useState({
      organization_id: "",
      contact_id: "",
      department_id: "",
      course_or_exam_id: "",
      product_instance_id: "",
      module_id: "",
      category_id: "",
      symptom_id: "",
      service_stage_id: "",
      ticket_type_id: "",
      environment: "",
      browser_device: "",
      source_url: "",
      exam_or_course_context: "",
    }),
    [savingNew, setSavingNew] = useState(false);

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
        setNewSubject(row.subject || "");
        setNewDescription(row.description || "");
        setNewChannel(row.channel || "");

        const detailRow = row as Ticket & Record<string, unknown>;

        setNewDetails({
          organization_id: String(detailRow.organization_id ?? ""),
          contact_id: String(detailRow.contact_id ?? ""),
          department_id: String(detailRow.department_id ?? ""),
          course_or_exam_id: String(detailRow.course_or_exam_id ?? ""),
          product_instance_id: String(detailRow.product_instance_id ?? ""),
          module_id: String(detailRow.module_id ?? ""),
          category_id: String(detailRow.category_id ?? ""),
          symptom_id: String(detailRow.symptom_id ?? ""),
          service_stage_id: String(detailRow.service_stage_id ?? ""),
          ticket_type_id: String(detailRow.ticket_type_id ?? ""),
          environment: "",
          browser_device: "",
          source_url: "",
          exam_or_course_context: "",
        });
        setReported(localDateTime(row.reported_at));

        // โหลดประวัติ (audit log) แยก ไม่ให้ล้มทั้งหน้าถ้าโหลดไม่ได้
        api<HistoryRow[]>(`/tickets/${id}/history`, {
          signal: controller.signal,
        })
          .then(setHistory)
          .catch(() => {
            if (!controller.signal.aborted) setHistory([]);
          });

        // map ชื่อผู้รับผิดชอบและผู้สร้างจากรายชื่อเดียวกัน
        try {
          const options = await api<{
            assignees: { id: number; name: string }[];
          }>(`/tickets/${id}/lifecycle-options`, {
            signal: controller.signal,
          });
          const nameOf = (uid: number | null | undefined) =>
            uid == null
              ? null
              : options.assignees.find((p) => p.id === uid)?.name ||
                `ผู้ใช้ #${uid}`;
          setAssigneeName(nameOf(row.assignee_id) || "ยังไม่มีผู้รับผิดชอบ");
          setCreatorName(nameOf(row.created_by_id) || "ไม่ทราบ");
        } catch {
          if (controller.signal.aborted) return;
          setAssigneeName(
            row.assignee_id
              ? `ผู้ใช้ #${row.assignee_id}`
              : "ยังไม่มีผู้รับผิดชอบ",
          );
          setCreatorName(
            row.created_by_id ? `ผู้ใช้ #${row.created_by_id}` : "ไม่ทราบ",
          );
        }
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [preview, session, id, attempt]);

  async function save(path: string, body: unknown): Promise<boolean> {
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

      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");

      return false;
    } finally {
      setSaving(false);
    }
  }

  const editable = !preview && session?.can_create_cases;
  const canEditNew = Boolean(
    !preview &&
      ticket?.status === "NEW" &&
      session &&
      (session.role === "Admin" ||
        [ticket.created_by_id, ticket.owner_id, ticket.assignee_id].includes(
          session.id,
        )),
  );

  async function saveNewDetails(event: FormEvent) {
    event.preventDefault();

    if (!ticket) return;

    setSavingNew(true);
    setError("");
    setMessage("");

    try {
      const payload = {
        subject: newSubject.trim(),
        description: newDescription.trim() || null,
        channel: newChannel || null,
      };

      const updated = await api<Ticket>(`/tickets/${id}/details`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      });

      setTicket(updated);
      setEditingNew(false);
      setMessage("บันทึกข้อมูลเคสแล้ว");
      setAttempt((n) => n + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกข้อมูลไม่สำเร็จ");
    } finally {
      setSavingNew(false);
    }
  }

  return (
    <AppShell title="รายละเอียดเคส">
      <div className="page-heading flex justify-between items-start">
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

        {/* Status Badge สีสันชัดเจน ตาม BR-01..13 */}
        {ticket && <StatusBadge status={ticket.status} />}
      </div>

      {error && (
        <ErrorState message={error} onRetry={() => setAttempt((n) => n + 1)} />
      )}

      {!ticket ? (
        !error && <TableSkeleton />
      ) : (
        <section className="surface detail-card">
          {!preview && session?.can_create_cases && (
            <LifecycleActions ticket={ticket} onUpdated={setTicket} />
          )}

          <div className="flex items-center justify-between gap-3">
            <h2>ข้อมูลเคส</h2>
            {canEditNew && !editingNew && (
              <Button type="button" onClick={() => setEditingNew(true)}>
                <Pencil size={14} /> แก้ไขข้อมูลเคส
              </Button>
            )}
          </div>
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
              ["ผู้รับผิดชอบ (Assigned To)", assigneeName],
              ["สร้างโดย (ผู้บันทึกจริง)", creatorName],
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

          {/* Audit log: ผู้บันทึกจริง (actor) แยกจากผู้รับผิดชอบ (owner) */}
          {!preview && (
            <section className="detail-edit" aria-label="ประวัติการดำเนินการ">
              <h3>ประวัติการดำเนินการ (Audit log)</h3>
              {history.length === 0 ? (
                <p className="text-muted text-xs">ยังไม่มีประวัติ</p>
              ) : (
                <ul>
                  {history.map((h) => (
                    <li key={h.id}>
                      <small>
                        {new Date(h.created_at).toLocaleString("th-TH")}
                      </small>{" "}
                      {h.details.event === "CASE_CREATED" ? (
                        <>
                          <strong>{h.actor_name}</strong> สร้างเคส
                          {h.details.created_for_user_id && h.owner_name ? (
                            <>
                              {" "}
                              แทน <strong>{h.owner_name}</strong>
                            </>
                          ) : null}
                        </>
                      ) : (
                        <>
                          <strong>{h.actor_name}</strong> เปลี่ยนสถานะ{" "}
                          {h.from_status
                            ? statusNames[h.from_status] || h.from_status
                            : "–"}{" "}
                          → {statusNames[h.to_status] || h.to_status}
                        </>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}

          {canEditNew && editingNew && (
            <form className="detail-edit" onSubmit={saveNewDetails}>
              <div className="flex items-center justify-between gap-2">
                <h3>แก้ไขข้อมูลเคส</h3>

                <Button type="button" onClick={() => setEditingNew(false)}>
                  <X size={14} /> ยกเลิก
                </Button>
              </div>

              <label>
                หัวข้อเคส
                <Input
                  maxLength={255}
                  required
                  value={newSubject}
                  onChange={setNewSubject}
                  placeholder="กรอกหัวข้อเคส"
                />
              </label>

              <label>
                ลูกค้า
                <div className="input">{customer || "ยังไม่ระบุลูกค้า"}</div>
                <span className="text-muted text-xs">แสดงลูกค้าปัจจุบัน</span>
              </label>

              <label>
                รายละเอียด
                <textarea
                  maxLength={20000}
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  placeholder="กรอกรายละเอียดของปัญหา"
                />
              </label>

              <label>
                ช่องทาง
                <select
                  className="input"
                  value={newChannel}
                  onChange={(e) => setNewChannel(e.target.value)}
                  required
                >
                  <option value="">เลือกช่องทาง</option>

                  {Object.entries(channelNames).map(([channelId, label]) => (
                    <option key={channelId} value={channelId}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>

              <div className="flex items-center gap-2">
                <Button type="button" onClick={() => setEditingNew(false)}>
                  ยกเลิก
                </Button>

                <Button type="submit" variant="primary" disabled={savingNew}>
                  {savingNew ? "กำลังบันทึก..." : "บันทึกการแก้ไข"}
                </Button>
              </div>
            </form>
          )}

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