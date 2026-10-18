"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Search, ArrowUpRight } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import { all } from "@/lib/api";
import type { Organization } from "@/lib/types";
import { previewRows } from "@/lib/preview";
import {
  EmptyState,
  ErrorState,
  TableSkeleton,
} from "@/components/ui/primitives";
export function CustomerScreen() {
  const { session, preview } = useSession();
  const [rows, setRows] = useState<Organization[] | null>(
      preview
        ? previewRows.map((r, i) => ({
            id: i + 1,
            name: r.customer,
            is_active: true,
          }))
        : null,
    ),
    [query, setQuery] = useState(""),
    [error, setError] = useState(""),
    [attempt, setAttempt] = useState(0);
  useEffect(() => {
    if (!session || preview) return;
    const controller = new AbortController();
    all<Organization>("/customers/organizations", controller.signal)
      .then(setRows)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [session, preview, attempt]);
  const filtered = rows?.filter((row) =>
    row.name.toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <AppShell title="Customers">
      <div className="page-heading">
        <div>
          <h1>ลูกค้า</h1>
          <p>ทะเบียนองค์กรลูกค้าและระบบที่ใช้งาน</p>
        </div>
        {!preview && (
          <Link href="/registry" className="button button-secondary">
            จัดการทะเบียนลูกค้า
            <ArrowUpRight size={14} />
          </Link>
        )}
      </div>
      <section className="surface">
        <div className="p-4">
          <div className="search-field">
            <Search size={16} />
            <input
              aria-label="ค้นหาลูกค้า"
              placeholder="ค้นหาชื่อองค์กรลูกค้า..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </div>
        </div>
        {error ? (
          <ErrorState
            message={error}
            onRetry={() => setAttempt((n) => n + 1)}
          />
        ) : !rows ? (
          <TableSkeleton />
        ) : (
          <>
            <table className="customer-list">
              <thead>
                <tr>
                  <th>องค์กรลูกค้า</th>
                  <th>สถานะ</th>
                </tr>
              </thead>
              <tbody>
                {filtered?.map((row) => (
                  <tr key={row.id}>
                    <td>{row.name}</td>
                    <td>
                      <span className="badge">
                        {row.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!filtered?.length && (
              <EmptyState
                title="ไม่พบลูกค้า"
                description="ลองค้นหาด้วยชื่อองค์กรอื่น หรือเพิ่มข้อมูลในทะเบียนลูกค้า"
              />
            )}
          </>
        )}
      </section>
    </AppShell>
  );
}
