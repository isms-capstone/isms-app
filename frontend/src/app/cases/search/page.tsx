"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { Button, Input } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import type { Ticket } from "@/lib/types";

type Option = { id: number; name: string };
type Options = {
  organizations: Option[];
  products: Option[];
  assignees: Option[];
  statuses: string[];
  can_share: boolean;
  can_export: boolean;
};
type Filters = {
  q?: string;
  status?: string | null;
  organization_id?: number | null;
  product_id?: number | null;
  assignee_id?: number | null;
  severity?: string | null;
  reported_from?: string | null;
  reported_before?: string | null;
};
type SearchResult = { items: Ticket[]; total: number };
type SavedView = {
  id: number;
  name: string;
  scope: "personal" | "team";
  filters: Filters;
};
const pageSize = 30;
const caseTime = new Intl.DateTimeFormat("th-TH", {
  dateStyle: "medium",
  timeZone: "Asia/Bangkok",
});

function shiftDate(date: string, days: number) {
  const value = new Date(`${date}T00:00:00Z`);
  value.setUTCDate(value.getUTCDate() + days);
  return value.toISOString().slice(0, 10);
}

export default function CaseSearchPage() {
  const [options, setOptions] = useState<Options | null>(null);
  const [views, setViews] = useState<SavedView[]>([]);
  const [form, setForm] = useState<Filters>({});
  const [applied, setApplied] = useState<Filters>({});
  const [result, setResult] = useState<SearchResult | null>(null);
  const [offset, setOffset] = useState(0);
  const [viewName, setViewName] = useState("");
  const [scope, setScope] = useState<SavedView["scope"]>("personal");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      api<Options>("/case-search/options", { signal: controller.signal }),
      api<SavedView[]>("/case-search/views", { signal: controller.signal }),
    ])
      .then(([choices, saved]) => {
        setOptions(choices);
        setViews(saved);
      })
      .catch((reason) => {
        if (!controller.signal.aborted) setError(reason.message);
      });
    return () => controller.abort();
  }, []);

  function change<Key extends keyof Filters>(key: Key, value: Filters[Key]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function action(run: () => Promise<void>) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await run();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "ดำเนินการไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  async function search(filters: Filters, nextOffset = 0) {
    await action(async () => {
      const response = await api<SearchResult>(
        `/case-search/query?limit=${pageSize}&offset=${nextOffset}`,
        {
          method: "POST",
          body: JSON.stringify(filters),
        },
      );
      setApplied(filters);
      setResult(response);
      setOffset(nextOffset);
    });
  }

  async function saveView(event: FormEvent) {
    event.preventDefault();
    await action(async () => {
      const saved = await api<SavedView>("/case-search/views", {
        method: "POST",
        body: JSON.stringify({ name: viewName, scope, filters: form }),
      });
      setViews((current) => [...current, saved]);
      setViewName("");
      setNotice(`บันทึกมุมมอง ${saved.name} แล้ว`);
    });
  }

  async function download(format: "csv" | "xlsx") {
    await action(async () => {
      const response = await fetch(
        `/api/backend/case-search/export/${format}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(applied),
        },
      );
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        throw new Error(
          typeof data?.detail === "string" ? data.detail : "ส่งออกไม่สำเร็จ",
        );
      }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `cases.${format}`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setNotice("เตรียมไฟล์ส่งออกแล้ว");
    });
  }

  const dropdown = (
    label: string,
    value: string | number | null | undefined,
    rows: { id: string | number; name: string }[],
    onChange: (value: string) => void,
  ) => (
    <label>
      {label}
      <select
        aria-label={label}
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded border border-[var(--line)] p-2"
      >
        <option value="">ทั้งหมด</option>
        {rows.map((row) => (
          <option value={row.id} key={row.id}>
            {row.name}
          </option>
        ))}
      </select>
    </label>
  );

  return (
    <AppShell title="ค้นหาเคส">
      <div className="space-y-4">
        <section className="surface detail-card space-y-4">
          <h1>ค้นหาเคส</h1>
          {error && (
            <p role="alert" className="form-error">
              {error}
            </p>
          )}
          {notice && <p role="status">{notice}</p>}
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault();
              void search(form);
            }}
          >
            <label>
              คำค้น
              <Input
                value={form.q ?? ""}
                maxLength={255}
                placeholder="หัวข้อ รายละเอียด บันทึกงาน หรือเลขเคส"
                onChange={(value) => change("q", value)}
              />
            </label>
            <div className="category-grid">
              {dropdown(
                "สถานะ",
                form.status,
                (options?.statuses ?? []).map((name) => ({ id: name, name })),
                (value) => change("status", value || null),
              )}
              {dropdown(
                "ลูกค้า",
                form.organization_id,
                options?.organizations ?? [],
                (value) =>
                  change("organization_id", value ? Number(value) : null),
              )}
              {dropdown(
                "ผลิตภัณฑ์",
                form.product_id,
                options?.products ?? [],
                (value) => change("product_id", value ? Number(value) : null),
              )}
              {dropdown(
                "ผู้รับผิดชอบ",
                form.assignee_id,
                options?.assignees ?? [],
                (value) => change("assignee_id", value ? Number(value) : null),
              )}
              {dropdown(
                "Severity",
                form.severity,
                ["S1", "S2", "S3", "S4"].map((name) => ({ id: name, name })),
                (value) => change("severity", value || null),
              )}
              <label>
                วันที่รับแจ้งตั้งแต่
                <Input
                  type="date"
                  value={form.reported_from?.slice(0, 10) ?? ""}
                  onChange={(value) =>
                    change(
                      "reported_from",
                      value ? `${value}T00:00:00+07:00` : null,
                    )
                  }
                />
              </label>
              <label>
                วันที่รับแจ้งถึง
                <Input
                  type="date"
                  value={
                    form.reported_before
                      ? shiftDate(form.reported_before.slice(0, 10), -1)
                      : ""
                  }
                  onChange={(value) =>
                    change(
                      "reported_before",
                      value ? `${shiftDate(value, 1)}T00:00:00+07:00` : null,
                    )
                  }
                />
              </label>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button
                type="submit"
                variant="primary"
                disabled={busy || !options}
              >
                ค้นหา
              </Button>
              <Button disabled={busy} onClick={() => setForm({})}>
                ล้างตัวกรอง
              </Button>
            </div>
          </form>
          <form className="flex flex-wrap items-end gap-2" onSubmit={saveView}>
            <label>
              ชื่อมุมมอง
              <Input
                value={viewName}
                required
                maxLength={100}
                onChange={setViewName}
              />
            </label>
            <label>
              แชร์กับ
              <select
                aria-label="แชร์กับ"
                value={scope}
                className="w-full rounded border border-[var(--line)] p-2"
                onChange={(event) =>
                  setScope(event.target.value === "team" ? "team" : "personal")
                }
              >
                <option value="personal">ส่วนตัว</option>
                {options?.can_share && <option value="team">ทีมของฉัน</option>}
              </select>
            </label>
            <Button
              type="submit"
              disabled={busy || !options || !viewName.trim()}
            >
              บันทึกมุมมอง
            </Button>
          </form>
          {views.length > 0 && (
            <div className="flex flex-wrap gap-2" aria-label="มุมมองที่บันทึก">
              {views.map((view) => (
                <Button
                  key={view.id}
                  disabled={busy}
                  onClick={() => {
                    setForm(view.filters);
                    void search(view.filters);
                  }}
                >
                  {view.name} · {view.scope === "team" ? "ทีม" : "ส่วนตัว"}
                </Button>
              ))}
            </div>
          )}
        </section>
        {result && (
          <section
            className="surface detail-card space-y-3"
            aria-label="ผลการค้นหา"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2>ผลการค้นหา {result.total} เคส</h2>
              {options?.can_export && (
                <div className="flex flex-wrap gap-2">
                  <Button disabled={busy} onClick={() => void download("csv")}>
                    ส่งออก CSV
                  </Button>
                  <Button disabled={busy} onClick={() => void download("xlsx")}>
                    ส่งออก Excel
                  </Button>
                </div>
              )}
            </div>
            {result.items.length === 0 && <p>ไม่พบเคสที่ตรงกับเงื่อนไข</p>}
            <ul className="space-y-2">
              {result.items.map((ticket) => (
                <li
                  key={ticket.id}
                  className="border-b border-[var(--line)] py-2"
                >
                  <Link
                    className="text-link break-words"
                    href={`/cases/${ticket.id}`}
                  >
                    {ticket.ticket_no ?? `#${ticket.id}`} ·{" "}
                    {ticket.subject ?? "ยังไม่ระบุหัวข้อ"}
                  </Link>
                  <p>
                    {ticket.status} · {ticket.severity ?? "ไม่ระบุ Severity"} ·{" "}
                    {caseTime.format(new Date(ticket.reported_at))}
                  </p>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-2">
              <Button
                disabled={busy || offset === 0}
                onClick={() =>
                  void search(applied, Math.max(0, offset - pageSize))
                }
              >
                หน้าก่อน
              </Button>
              <Button
                disabled={busy || offset + pageSize >= result.total}
                onClick={() => void search(applied, offset + pageSize)}
              >
                หน้าถัดไป
              </Button>
            </div>
          </section>
        )}
      </div>
    </AppShell>
  );
}
