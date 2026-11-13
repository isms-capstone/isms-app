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
                        {row.ticket_no ?? `#${row.ticket_id}`}
                      </Link>
                    </td>
                    <td>{row.actor ?? `#${row.actor_id}`}</td>
                    <td>
                      <details>
                        <summary>{row.event}</summary>
                        <pre className="whitespace-pre-wrap break-all">
                          {JSON.stringify(row.changes, null, 2)}
                        </pre>
                      </details>
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
