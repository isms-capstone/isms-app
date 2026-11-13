"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import { Button, Input } from "@/components/ui/primitives";
import { api } from "@/lib/api";

type AuditPage = {
  has_more: boolean;
  rows: {
    id: number;
    ticket_id: number;
    ticket_no: string | null;
    event: string;
    actor: string | null;
    actor_id: number;
    created_at: string;
    changes: Record<string, unknown>;
  }[];
};

const eventLabels: Record<string, string> = {
  relationship_created: "เชื่อมโยงเคส",
  duplicate_merged: "รวมเคสซ้ำ",
  relationship_closure_notice: "บันทึกการแจ้งปิดเคส",
  similarity_decision: "เลือกแนวทางจากเคสที่คล้ายกัน",
  worklog_created: "บันทึกการสื่อสาร",
  categorization_created: "บันทึกหมวดหมู่",
  categorization_updated: "แก้ไขหมวดหมู่",
  request_start: "เริ่มดำเนินคำขอ",
  request_fulfil: "ส่งมอบผลคำขอ",
  request_confirm: "ยืนยันและปิดคำขอ",
};

const fieldLabels: Record<string, string> = {
  related_ticket_id: "เคสที่เชื่อมโยง",
  master_ticket_id: "เคสหลัก",
  source_ticket_id: "เคสต้นทาง",
  chosen_ticket_id: "เคสที่เลือก",
  relationship_type: "ประเภทความสัมพันธ์",
  reason: "เหตุผล",
  delivery_status: "สถานะการแจ้ง",
  organization_id: "รหัสองค์กร",
  contact_id: "รหัสผู้แจ้ง",
  message: "ข้อความ",
  channel: "ช่องทาง",
};

const values: Record<string, Record<string, string>> = {
  relationship_type: {
    related: "เกี่ยวข้องกัน",
    duplicate: "เคสซ้ำ",
    "follow-up": "ติดตามผล",
    "caused-by": "เกิดจาก",
    "child-of": "เคสย่อยของเหตุการณ์หลัก",
  },
  delivery_status: { pending: "รอส่ง" },
};

function auditValue(field: string, value: unknown): React.ReactNode {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "ใช่" : "ไม่ใช่";
  if (typeof value === "number" && ["related_ticket_id", "master_ticket_id", "source_ticket_id", "chosen_ticket_id"].includes(field)) {
    return <Link className="text-link" href={`/cases/${value}`}>เคส #{value}</Link>;
  }
  if (Array.isArray(value)) return value.length ? value.map((item, index) => <span key={index}>{index > 0 && ", "}{auditValue(field, item)}</span>) : "—";
  if (typeof value === "object") {
    if ("new" in value) return <>{auditValue(field, "old" in value ? value.old : null)} → {auditValue(field, value.new)}</>;
    return <ul>{Object.entries(value).map(([key, item]) => <li key={key}>{fieldLabels[key] ?? key.replaceAll("_", " ")} · {auditValue(key, item)}</li>)}</ul>;
  }
  return values[field]?.[String(value)] ?? String(value);
}

const pageSize = 50;

export default function Page() {
  const { session } = useSession();
  const [filters, setFilters] = useState({ q: "", start: "", end: "" });
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<AuditPage>();
  const [error, setError] = useState("");

  useEffect(() => {
    if (session?.role !== "Admin") return;
    const controller = new AbortController();
    api<AuditPage>(
      `/admin/audit-log?limit=${pageSize}&offset=${offset}&${search}`,
      {
        signal: controller.signal,
      },
    )
      .then((result) => {
        setError("");
        setData(result);
      })
      .catch((error) => {
        if (!controller.signal.aborted) setError(error.message);
      });
    return () => controller.abort();
  }, [session, search, offset]);

  return (
    <AppShell title="Audit Log">
      <div className="page-heading">
        <div>
          <h1>Audit Log</h1>
        </div>
      </div>
      {session?.role === "Admin" ? (
        <section className="surface detail-card">
          <form
            className="mb-4 space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              const query = new URLSearchParams();
              for (const [key, value] of Object.entries(filters))
                if (value.trim()) query.set(key, value.trim());
              if (query.toString() !== search || offset !== 0) {
                setData(undefined);
                setError("");
                setOffset(0);
                setSearch(query.toString());
              }
            }}
          >
            <div className="detail-grid">
              <label>
                คำค้น
                <Input
                  value={filters.q}
                  maxLength={255}
                  placeholder="เลขเคส ผู้กระทำ เหตุการณ์ หรือเหตุผล"
                  onChange={(value) => setFilters({ ...filters, q: value })}
                />
              </label>
              <label>
                ตั้งแต่ (UTC)
                <Input
                  type="date"
                  value={filters.start}
                  onChange={(value) => setFilters({ ...filters, start: value })}
                />
              </label>
              <label>
                ถึงวันที่ (UTC)
                <Input
                  type="date"
                  value={filters.end}
                  min={filters.start || undefined}
                  onChange={(value) => setFilters({ ...filters, end: value })}
                />
              </label>
            </div>
            <Button type="submit">ค้นหา</Button>
          </form>
          {error && <p role="alert">{error}</p>}
          {!data && !error && <p role="status">กำลังโหลด Audit Log</p>}
          {data?.rows.length === 0 && <p>ไม่พบรายการ</p>}
          {!!data?.rows.length && (
            <table className="customer-list">
              <thead>
                <tr>
                  <th>เวลา</th>
                  <th>เคส</th>
                  <th>ผู้กระทำ</th>
                  <th>เหตุการณ์</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((row) => (
                  <tr key={row.id}>
                    <td>{new Date(row.created_at).toLocaleString("th-TH")}</td>
                    <td>
                      <Link
                        className="text-link"
                        href={`/cases/${row.ticket_id}`}
                      >
                        {row.ticket_no ?? "เปิดเคส"}
                      </Link>
                      <small className="block mt-1 whitespace-nowrap">
                        ID เคส #{row.ticket_id}
                      </small>
                    </td>
                    <td>{row.actor ?? `#${row.actor_id}`}</td>
                    <td className="align-top" style={{ textAlign: "start" }}>
                      <strong>{eventLabels[row.event] ?? row.event.replaceAll("_", " ")}</strong>
                      {Object.keys(row.changes ?? {}).length > 0 && (
                        <details>
                          <summary className="timeline-detail-trigger">ดูรายละเอียด</summary>
                          <dl className="space-y-2">
                            {row.event === "relationship_closure_notice" && (
                              <div>
                                <dt className="font-semibold">
                                  {row.ticket_id === row.changes.master_ticket_id ? "แจ้งปิดสำหรับเคสหลัก" : "แจ้งปิดสำหรับเคสที่เชื่อมไว้"}
                                </dt>
                                <dd>{auditValue("related_ticket_id", row.ticket_id)}</dd>
                              </div>
                            )}
                            {Object.entries(row.changes).map(([field, value]) => (
                              <div key={field}>
                                <dt className="font-semibold">{fieldLabels[field] ?? field.replaceAll("_", " ")}</dt>
                                <dd className="break-words">{auditValue(field, value)}</dd>
                              </div>
                            ))}
                          </dl>
                        </details>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="mt-4 flex gap-2">
            <Button
              disabled={!offset || !data}
              onClick={() => {
                setData(undefined);
                setOffset(offset - pageSize);
              }}
            >
              ก่อนหน้า
            </Button>
            <Button
              disabled={!data?.has_more}
              onClick={() => {
                setData(undefined);
                setOffset(offset + pageSize);
              }}
            >
              ถัดไป
            </Button>
          </div>
        </section>
      ) : (
        session && <p>เฉพาะผู้ดูแลระบบ</p>
      )}
    </AppShell>
  );
}
