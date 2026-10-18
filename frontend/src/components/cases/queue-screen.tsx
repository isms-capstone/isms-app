"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { StatCard, Segment } from "@DeverhoodHT/get-design";
import {
  Plus,
  Clock3,
  Search,
  SlidersHorizontal,
  RefreshCw,
  Download,
  Bookmark,
  UserPlus,
  Tag,
  Check,
  X,
  Settings2,
} from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import {
  Button,
  ErrorState,
  TableSkeleton,
  cx,
} from "@/components/ui/primitives";
import { queueData } from "@/lib/api";
import { previewData, previewNow } from "@/lib/preview";
import { channelNames, openStatuses, type QueueData } from "@/lib/types";
import { CaseTable } from "./case-table";
import { DraftList } from "./draft-list";
import { emptyFilters, FilterDrawer, type Filters } from "./filters";
type Scope = "all" | "open" | "mine" | "unassigned" | "today" | "risk";
export function QueueScreen({
  view = "work",
  initialQuery = "",
  product,
}: {
  view?: "work" | "all" | "unassigned";
  initialQuery?: string;
  product?: string;
}) {
  const { session, preview, href } = useSession();
  const [data, setData] = useState<QueueData | null>(
      preview ? previewData : null,
    ),
    [error, setError] = useState(""),
    [refreshing, setRefreshing] = useState(false),
    [updated, setUpdated] = useState<Date | null>(null);
  const [query, setQuery] = useState(initialQuery),
    [scope, setScope] = useState<Scope>(
      view === "unassigned" ? "unassigned" : view === "all" ? "open" : "all",
    );
  const [filters, setFilters] = useState<Filters>({ ...emptyFilters }),
    [pending, setPending] = useState<Filters>({ ...emptyFilters }),
    [drawer, setDrawer] = useState(false),
    [page, setPage] = useState(1),
    [pageSize, setPageSize] = useState(25),
    [selected, setSelected] = useState<Set<number>>(new Set()),
    [sort, setSort] = useState("sla");
  const requestRef = useRef<AbortController | null>(null);
  const [mountedAt] = useState(
    () => new Date(preview ? previewNow : Date.now()),
  );
  const now = updated || mountedAt;
  const load = useCallback(async () => {
    if (preview || !session) return;
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    try {
      const result = await queueData(session, controller.signal);
      if (!controller.signal.aborted) {
        setData(result);
        setError("");
        setUpdated(new Date());
      }
    } catch (e) {
      if (!controller.signal.aborted)
        setError(e instanceof Error ? e.message : "โหลดคิวเคสไม่สำเร็จ");
    } finally {
      if (!controller.signal.aborted) setRefreshing(false);
    }
  }, [preview, session]);
  useEffect(() => {
    const initial = setTimeout(load, 0);
    const interval = setInterval(load, 60000);
    return () => {
      clearTimeout(initial);
      clearInterval(interval);
      requestRef.current?.abort();
    };
  }, [load]);
  const slaAvailable = !!data?.rows.some((row) => row.slaSeconds !== null);
  const rows = useMemo(() => {
    if (!data) return [];
    return data.rows
      .filter((row) => {
        if (row.status === "DRAFT") return false;
        if (view !== "all" && !openStatuses.includes(row.status)) return false;
        if (
          scope === "open" &&
          !filters.statuses.length &&
          !openStatuses.includes(row.status)
        )
          return false;
        if (product && row.product.toLowerCase() !== product.toLowerCase())
          return false;
        if (scope === "mine" && row.assignee_id !== session?.id) return false;
        if (scope === "unassigned" && row.assignee_id !== null) return false;
        if (
          scope === "today" &&
          new Date(row.created_at).toLocaleDateString("en-CA", {
            timeZone: "Asia/Bangkok",
          }) !== now.toLocaleDateString("en-CA", { timeZone: "Asia/Bangkok" })
        )
          return false;
        if (scope === "risk" && (row.slaRatio === null || row.slaRatio >= 0.25))
          return false;
        if (
          query.trim() &&
          !`${row.ticket_no} ${row.subject} ${row.customer} ${row.assignee}`
            .toLocaleLowerCase()
            .includes(query.toLocaleLowerCase().trim())
        )
          return false;
        if (filters.statuses.length && !filters.statuses.includes(row.status))
          return false;
        if (filters.products.length && !filters.products.includes(row.product))
          return false;
        if (
          filters.priorities.length &&
          !filters.priorities.includes(row.severity || "")
        )
          return false;
        if (
          filters.channels.length &&
          !filters.channels.includes(row.channel || "")
        )
          return false;
        if (
          filters.tiers.length &&
          !filters.tiers.includes(String(row.current_tier))
        )
          return false;
        if (
          (filters.assignee === "mine" && row.assignee_id !== session?.id) ||
          (filters.assignee === "unassigned" && row.assignee_id !== null)
        )
          return false;
        if (filters.sla.length) {
          const state =
            row.slaSeconds === null
              ? "none"
              : row.slaSeconds < 0
                ? "breached"
                : row.slaRatio !== null && row.slaRatio < 0.25
                  ? "risk"
                  : "safe";
          if (!filters.sla.includes(state)) return false;
        }
        const date = Date.parse(row.created_at);
        if (
          filters.date === "today" &&
          new Date(date).toLocaleDateString("en-CA", {
            timeZone: "Asia/Bangkok",
          }) !== now.toLocaleDateString("en-CA", { timeZone: "Asia/Bangkok" })
        )
          return false;
        if (filters.date === "7days" && date < now.getTime() - 7 * 86400000)
          return false;
        if (
          filters.date === "custom" &&
          ((filters.from &&
            date < Date.parse(`${filters.from}T00:00:00+07:00`)) ||
            (filters.to &&
              date > Date.parse(`${filters.to}T23:59:59.999+07:00`)))
        )
          return false;
        return true;
      })
      .sort((a, b) =>
        sort === "sla" && slaAvailable
          ? (a.slaSeconds ?? Infinity) - (b.slaSeconds ?? Infinity)
          : Date.parse(b.created_at) - Date.parse(a.created_at),
      );
  }, [
    data,
    view,
    product,
    scope,
    session?.id,
    query,
    filters,
    sort,
    slaAvailable,
    now,
  ]);
  const title =
    product ||
    {
      work: "งานของฉัน",
      all: "เคสทั้งหมด",
      unassigned: "ยังไม่มีผู้รับผิดชอบ",
    }[view];
  const setScopeAndReset = (next: Scope) => {
    setScope(next);
    setPage(1);
    setSelected(new Set());
  };
  const apply = (next: Filters) => {
    setFilters(next);
    setPage(1);
    setSelected(new Set());
  };
  const openDrawer = () => {
    setPending(structuredClone(filters));
    setDrawer(true);
  };
  const activeCount = Object.entries(filters).reduce(
    (count, [key, value]) =>
      count +
      (Array.isArray(value)
        ? value.length
        : key === "assignee" || key === "date"
          ? Number(value !== "any")
          : 0),
    0,
  );
  const tabs = (
    <Segment
      aria-label="มุมมองคิว"
      value={scope}
      onChange={(value) => setScopeAndReset(value as Scope)}
      options={[
        { value: "all", label: "ทั้งหมด" },
        { value: "mine", label: "งานของฉัน" },
        { value: "unassigned", label: "ยังไม่มีผู้รับ" },
      ]}
    />
  );
  const quickFilters = (
    <>
      <select
        aria-label="กรองผลิตภัณฑ์"
        className="filter-select"
        value={filters.products[0] || ""}
        onChange={(e) =>
          apply({
            ...filters,
            products: e.target.value ? [e.target.value] : [],
          })
        }
      >
        <option value="">Product</option>
        {data?.products.map((p) => (
          <option key={p.id}>{p.name}</option>
        ))}
      </select>
      <select
        aria-label="กรอง Priority"
        className="filter-select"
        value={filters.priorities[0] || ""}
        onChange={(e) =>
          apply({
            ...filters,
            priorities: e.target.value ? [e.target.value] : [],
          })
        }
      >
        <option value="">Priority</option>
        {["S1", "S2", "S3", "S4"].map((s) => (
          <option key={s}>{s}</option>
        ))}
      </select>
      <select
        aria-label="กรอง Tier"
        className="filter-select"
        value={filters.tiers[0] || ""}
        onChange={(e) =>
          apply({ ...filters, tiers: e.target.value ? [e.target.value] : [] })
        }
      >
        <option value="">Tier</option>
        {["0", "1", "2"].map((s) => (
          <option key={s} value={s}>
            Tier {s}
          </option>
        ))}
      </select>
      <select
        aria-label="กรองช่องทาง"
        className="filter-select"
        value={filters.channels[0] || ""}
        onChange={(e) =>
          apply({
            ...filters,
            channels: e.target.value ? [e.target.value] : [],
          })
        }
      >
        <option value="">Channel</option>
        {Object.entries(channelNames).map(([id, label]) => (
          <option key={id} value={id}>
            {label}
          </option>
        ))}
      </select>
      <select
        aria-label="กรอง SLA"
        className="filter-select"
        disabled={!slaAvailable}
        title={!slaAvailable ? "รอข้อมูลจากระบบ SLA" : undefined}
        value={filters.sla[0] || ""}
        onChange={(e) =>
          apply({ ...filters, sla: e.target.value ? [e.target.value] : [] })
        }
      >
        <option value="">SLA</option>
        <option value="breached">Breached</option>
        <option value="risk">At risk</option>
        <option value="safe">On track</option>
      </select>
      <Button onClick={openDrawer} className="more-filters">
        <SlidersHorizontal size={15} />
        ตัวกรองเพิ่มเติม
        {activeCount > 0 && <span className="small-count">{activeCount}</span>}
      </Button>
    </>
  );
  const search = (
    <div className="search-field">
      <Search size={17} />
      <input
        aria-label="ค้นหาเคส"
        placeholder={
          view === "all"
            ? "ค้นหาเลขเคส, หัวข้อ, ลูกค้า, ผู้รับผิดชอบ..."
            : "ค้นหาเคส ลูกค้า หรือผู้รับผิดชอบ..."
        }
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setPage(1);
        }}
      />
      {query && (
        <button onClick={() => setQuery("")} aria-label="ล้างคำค้น">
          <X size={14} />
        </button>
      )}
    </div>
  );
  function exportCsv() {
    const selectedRows = selected.size
      ? rows.filter((r) => selected.has(r.id))
      : rows;
    const cell = (value: unknown) =>
      `"${String(value ?? "")
        .replace(/^[=+@\-]/, "'$&")
        .replaceAll('"', '""')}"`;
    const csv =
      "\uFEFF" +
      [
        [
          "Case",
          "Subject",
          "Customer",
          "Product",
          "Priority",
          "Status",
          "Channel",
        ],
        ...selectedRows.map((r) => [
          r.ticket_no,
          r.subject,
          r.customer,
          r.product,
          r.severity,
          r.status,
          channelNames[r.channel || ""],
        ]),
      ]
        .map((row) => row.map(cell).join(","))
        .join("\r\n");
    const url = URL.createObjectURL(
      new Blob([csv], { type: "text/csv;charset=utf-8" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "isms-cases.csv";
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <AppShell
      title={title}
      counts={
        data
          ? { mine: data.summary.mine, unassigned: data.summary.unassigned }
          : undefined
      }
    >
      <div className={cx("queue-page", view === "all" && "all-cases-page")}>
        <div className="page-heading">
          <div>
            <h1>
              {title}
              {view === "work" && !product && (
                <span className="heading-date">
                  {preview
                    ? "วันจันทร์ที่ 8 กันยายน"
                    : now.toLocaleDateString("th-TH", {
                        weekday: "long",
                        day: "numeric",
                        month: "long",
                        timeZone: "Asia/Bangkok",
                      })}
                </span>
              )}
            </h1>
            <p>
              {view === "all"
                ? "ค้นหา ตรวจสอบ และจัดการเคสทั้งหมดในระบบ"
                : slaAvailable
                  ? "ดูเคสที่ต้องดำเนินการ โดยเรียงตามเวลาที่เหลือของ SLA"
                  : "ดูเคสที่ต้องดำเนินการและเคสร่างของคุณ"}
            </p>
            {view === "all" && (
              <small>แสดงเคสทั้งหมดที่ผู้ใช้มีสิทธิ์เข้าถึง</small>
            )}
          </div>
          <div className="heading-actions">
            {view === "all" ? (
              <>
                <Button disabled title="Saved Views ยังไม่เปิดใช้งาน">
                  <Bookmark size={14} />
                  Save View
                </Button>
                <Button onClick={exportCsv} disabled={!rows.length}>
                  <Download size={14} />
                  Export
                </Button>
              </>
            ) : (
              <span className="last-updated">
                <span className="healthy-dot" />
                อัปเดตล่าสุด{" "}
                {preview
                  ? "14:08"
                  : updated?.toLocaleTimeString("th-TH", {
                      hour: "2-digit",
                      minute: "2-digit",
                    }) || "—"}{" "}
                · อัปเดตอัตโนมัติทุก 60 วินาที
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="อัปเดตคิวเคส"
                  onClick={() => {
                    setRefreshing(true);
                    if (preview) setRefreshing(false);
                    else load();
                  }}
                >
                  <RefreshCw
                    size={13}
                    className={cx(refreshing && "animate-spin")}
                  />
                </Button>
              </span>
            )}
            {view === "all" && session?.can_create_cases && (
              <Link href={href("/cases/new")} className="button button-primary">
                <Plus size={16} />
                สร้างเคส
              </Link>
            )}
          </div>
        </div>
        {view === "work" && !product && (
          <div className="action-counts">
            {[
              {
                count: data?.summary.unassigned,
                label: "ยังไม่มีผู้รับผิดชอบ",
                icon: "users",
                scope: "unassigned" as Scope,
                style: "unassigned",
              },
              {
                count: data?.summary.sla_at_risk,
                label: "เหลือเวลา SLA ไม่ถึง 25%",
                icon: "clock",
                scope: "risk" as Scope,
                style: "risk",
              },
              {
                count: data?.summary.mine,
                label: "งานของฉันที่เปิดอยู่",
                icon: "user",
                scope: "mine" as Scope,
                style: "mine",
              },
              {
                count: data?.summary.today,
                label: "เคสเข้าใหม่วันนี้",
                icon: "folder",
                scope: "today" as Scope,
                style: "incoming",
              },
            ].map((item) => (
              <button
                key={item.scope}
                className={`native-stat-action stat-${item.style}`}
                aria-pressed={scope === item.scope}
                onClick={() => setScopeAndReset(item.scope)}
                disabled={item.scope === "risk" && !slaAvailable}
                title={
                  item.scope === "risk" && !slaAvailable
                    ? "รอข้อมูลจากระบบ SLA"
                    : undefined
                }
              >
                <StatCard
                  size="small"
                  label={item.label}
                  value={item.count ?? "—"}
                  icon
                  iconName={item.icon}
                  iconColor="brand"
                  classNames={{
                    root: "work-stat",
                    icon: "work-stat-icon",
                    label: "work-stat-label",
                    value: "work-stat-value",
                    content: "work-stat-content",
                  }}
                />
              </button>
            ))}
          </div>
        )}
        {view === "all" && (
          <>
            <section className="surface all-search-panel">
              {search}
              <p>
                ค้นหาใน: <span className="search-scope-dot" />
                เลขเคส / หัวข้อ / ลูกค้า / ผู้รับผิดชอบ
              </p>
            </section>
            <div className="saved-views">
              <span>มุมมอง:</span>
              {(
                [
                  ["open", "All Open Cases"],
                  ["all", "All Cases"],
                  ["mine", "My Cases"],
                  ["unassigned", "Unassigned"],
                  ["risk", "SLA At Risk"],
                ] as const
              ).map(([value, label]) => (
                <button
                  key={value}
                  className={cx(scope === value && "active")}
                  disabled={value === "risk" && !slaAvailable}
                  onClick={() => setScopeAndReset(value)}
                >
                  {label}
                </button>
              ))}
              <Button variant="ghost" onClick={openDrawer}>
                <SlidersHorizontal size={14} />
                ตัวกรอง
              </Button>
            </div>
          </>
        )}
        <section className="surface queue-surface">
          {view !== "all" ? (
            <>
              <div className="queue-heading">
                <h2>
                  {product
                    ? `เคสที่เปิดอยู่ (${product})`
                    : "คิวเคสที่เปิดอยู่"}
                </h2>
                {tabs}
                <div className="queue-heading-actions">
                  <label className="sort-control">
                    เรียงตาม:
                    <select
                      aria-label="เรียงคิวเคส"
                      value={slaAvailable ? sort : "recent"}
                      onChange={(e) => setSort(e.target.value)}
                    >
                      <option value="sla" disabled={!slaAvailable}>
                        SLA เหลือน้อยที่สุด ↓
                      </option>
                      <option value="recent">บันทึกล่าสุด ↓</option>
                    </select>
                  </label>
                  {session?.can_create_cases && (
                    <Link
                      href={href("/cases/new")}
                      className="button button-primary"
                    >
                      <Plus size={16} />
                      สร้างเคส
                    </Link>
                  )}
                </div>
              </div>
              <div className="queue-toolbar">
                <div className="quick-filters">{quickFilters}</div>
                {search}
              </div>
            </>
          ) : (
            <div className="bulk-toolbar">
              <span className="selected-count">
                <Check size={14} />
                เลือกแล้ว {selected.size} เคส
              </span>
              <Button disabled title="ยังไม่มี API สำหรับเปลี่ยนผู้รับผิดชอบ">
                <UserPlus size={14} />
                Assign
              </Button>
              <Button disabled title="ยังไม่มี API สำหรับเปลี่ยนสถานะ">
                Change Status
              </Button>
              <Button disabled title="ยังไม่มี API สำหรับเปลี่ยน Priority">
                Change Priority
              </Button>
              <Button disabled title="ยังไม่มีระบบ Tag">
                <Tag size={14} />
                Add Tag
              </Button>
              <Button onClick={exportCsv} disabled={!rows.length}>
                <Download size={14} />
                Export
              </Button>
              <Button
                size="icon"
                aria-label="ตัวกรองคอลัมน์"
                onClick={openDrawer}
              >
                <Settings2 size={16} />
              </Button>
            </div>
          )}
          {activeCount > 0 && (
            <div className="applied-filters">
              <span>ใช้ตัวกรอง {activeCount} เงื่อนไข</span>
              {filters.products.map((name) => (
                <button
                  key={name}
                  onClick={() =>
                    apply({
                      ...filters,
                      products: filters.products.filter((p) => p !== name),
                    })
                  }
                >
                  {name}
                  <X size={12} />
                </button>
              ))}
              <button
                className="clear-filters"
                onClick={() => apply({ ...emptyFilters })}
              >
                ล้างทั้งหมด
              </button>
            </div>
          )}
          {error ? (
            <ErrorState message={error} onRetry={load} />
          ) : !data ? (
            <TableSkeleton />
          ) : (
            <CaseTable
              rows={rows}
              variant={view === "all" ? "all" : "work"}
              page={page}
              pageSize={pageSize}
              onPage={setPage}
              onPageSize={setPageSize}
              selected={selected}
              onSelected={setSelected}
            />
          )}
          {!preview && data && !slaAvailable && (
            <div className="data-note">
              <Clock3 size={13} />
              ยังไม่มีข้อมูล SLA จาก Backend · ใช้เวลาบันทึกล่าสุดในการเรียงคิว
            </div>
          )}
        </section>
        {view === "work" && !product && data && (
          <DraftList rows={data.drafts} onRefresh={load} />
        )}
        <FilterDrawer
          open={drawer}
          onClose={() => setDrawer(false)}
          value={pending}
          onChange={setPending}
          onApply={() => {
            apply(pending);
            setDrawer(false);
          }}
          products={data?.products || []}
          slaAvailable={slaAvailable}
        />
      </div>
    </AppShell>
  );
}
