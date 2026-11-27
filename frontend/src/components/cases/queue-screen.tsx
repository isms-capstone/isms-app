"use client";
import { SelectControl } from "@/components/ui/company-fields";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { StatCard, Segment, Search as GetSearch } from "@DeverhoodHT/get-design";
import { Plus, SlidersHorizontal, RefreshCw, X, Search as SearchIcon } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import { Button, ErrorState, TableSkeleton, cx } from "@/components/ui/primitives";
import { queueData, type QueueQuery } from "@/lib/api";
import { previewData, previewNow } from "@/lib/preview";
import {
  channelNames,
  severityNames,
  statusNames,
  tierNames,
  type QueueData,
} from "@/lib/types";
import { CaseTable } from "./case-table";
import { DraftList } from "./draft-list";
import { emptyFilters, FilterDrawer, type Filters } from "./filters";

type Scope = "open" | "all" | "mine" | "team" | "unassigned" | "today" | "risk";
const EXPORT_ROLES = new Set(["Admin", "Team Lead", "Executive"]);

function useDebounced<T>(value: T, delay: number) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

function dateRange(filters: Filters, now: Date) {
  const day = (date: Date) =>
    date.toLocaleDateString("en-CA", { timeZone: "Asia/Bangkok" });
  if (filters.date === "today") return { from: day(now), to: day(now) };
  if (filters.date === "7days")
    return { from: day(new Date(now.getTime() - 6 * 86400000)), to: day(now) };
  if (filters.date === "custom")
    return { from: filters.from || undefined, to: filters.to || undefined };
  return {};
}

export function QueueScreen({
  view = "work",
  initialQuery = "",
  product,
}: {
  view?: "work" | "all" | "unassigned";
  initialQuery?: string;
  /** Product code from the URL, e.g. "examplus". */
  product?: string;
}) {
  const { session, preview, href } = useSession();
  const [data, setData] = useState<QueueData | null>(preview ? previewData : null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(false),
    [updated, setUpdated] = useState<Date | null>(null);
  const [query, setQuery] = useState(initialQuery),
    [scope, setScope] = useState<Scope>(view === "unassigned" ? "unassigned" : "open"),
    [filters, setFilters] = useState<Filters>({ ...emptyFilters }),
    [pending, setPending] = useState<Filters>({ ...emptyFilters }),
    [drawer, setDrawer] = useState(false),
    [page, setPage] = useState(1),
    [pageSize, setPageSize] = useState(25),
    [selected, setSelected] = useState<Set<number>>(new Set()),
    [sort, setSort] = useState("sla");
  const searchText = useDebounced(query, 300);
  const requestRef = useRef<AbortController | null>(null);
  const [mountedAt] = useState(() => new Date(preview ? previewNow : Date.now()));
  const now = updated || mountedAt;
  const withDrafts = view === "work" && !product;

  const request = useMemo<QueueQuery>(() => {
    const range = dateRange(filters, mountedAt);
    return {
      scope,
      product: product || filters.products[0],
      statuses: filters.statuses,
      severities: filters.priorities,
      tiers: filters.tiers,
      channels: filters.channels,
      sla: filters.sla,
      assignee: filters.assignee,
      createdFrom: range.from,
      createdTo: range.to,
      q: searchText,
      sort,
      offset: (page - 1) * pageSize,
      limit: pageSize,
    };
  }, [scope, product, filters, searchText, sort, page, pageSize, mountedAt]);

  const load = useCallback(async () => {
    if (preview || !session) return;
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    setLoading(true);
    try {
      const result = await queueData(request, controller.signal, withDrafts);
      if (!controller.signal.aborted) {
        setData(result);
        setError("");
        setUpdated(new Date());
      }
    } catch (e) {
      if (!controller.signal.aborted)
        setError(e instanceof Error ? e.message : "โหลดรายการเคสไม่สำเร็จ");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [preview, session, request, withDrafts]);

  useEffect(() => {
    const initial = setTimeout(load, 0);
    const interval = setInterval(load, 60000);
    return () => {
      clearTimeout(initial);
      clearInterval(interval);
      requestRef.current?.abort();
    };
  }, [load]);

  // Design preview has no API, so apply the same filters to the sample rows.
  const visibleRows = useMemo(() => {
    if (!preview || !data) return data?.rows ?? [];
    const productLabel = request.product
      ? data.products.find((row) => row.code === request.product)?.name ?? request.product
      : "";
    const text = request.q.trim().toLowerCase();
    return data.rows.filter(
      (row) =>
        (!productLabel || row.product === productLabel) &&
        (!request.severities.length || request.severities.includes(row.severity ?? "")) &&
        (!request.statuses.length || request.statuses.includes(row.status)) &&
        (!request.channels.length || request.channels.includes(row.channel ?? "")) &&
        (!text ||
          [row.ticket_no, row.subject, row.customer].some((value) =>
            String(value ?? "").toLowerCase().includes(text),
          )),
    );
  }, [preview, data, request]);

  const productName =
    product &&
    (data?.products.find((p) => p.code === product)?.name ?? product);
  const title =
    productName ||
    { work: "งานของฉัน", all: "เคสทั้งหมด", unassigned: "เคสที่ยังไม่มีผู้รับ" }[view];
  const reset = () => {
    setPage(1);
    setSelected(new Set());
  };
  const changeScope = (next: Scope) => {
    setScope(next);
    reset();
  };
  const apply = (next: Filters) => {
    setFilters(next);
    reset();
  };
  const activeCount =
    filters.statuses.length +
    filters.products.length +
    filters.priorities.length +
    filters.tiers.length +
    filters.channels.length +
    filters.sla.length +
    Number(filters.assignee !== "any") +
    Number(filters.date !== "any");

  const single = (
    key: "products" | "priorities" | "tiers" | "channels" | "sla",
    label: string,
    placeholder: string,
    options: [string, string][],
  ) => (
    <SelectControl
      aria-label={label}
      className="filter-select"
      value={filters[key][0] || ""}
      onValueChange={(next) => apply({ ...filters, [key]: next ? [next] : [] })}
    >
      <option value="">{placeholder}</option>
      {options.map(([value, text]) => (
        <option key={value} value={value}>
          {text}
        </option>
      ))}
    </SelectControl>
  );
  const quickFilters = (
    <>
      {!product &&
        single(
          "products",
          "กรองตามผลิตภัณฑ์",
          "ผลิตภัณฑ์",
          (data?.products || []).map((p) => [p.code, p.name]),
        )}
      {single(
        "priorities",
        "กรองตามความรุนแรง",
        "ความรุนแรง",
        Object.entries(severityNames).map(([v, label]) => [v, `${v} ${label}`]),
      )}
      {single("tiers", "กรองตาม Tier", "Tier", Object.entries(tierNames).reverse())}
      {single("channels", "กรองตามช่องทาง", "ช่องทาง", Object.entries(channelNames))}
      {single("sla", "กรองตาม SLA", "SLA", [
        ["breached", "เกิน SLA แล้ว"],
        ["risk", "ใกล้ครบกำหนด"],
        ["safe", "ทันเวลา"],
      ])}
      <Button
        onClick={() => {
          setPending(structuredClone(filters));
          setDrawer(true);
        }}
        className="more-filters"
      >
        <SlidersHorizontal size={15} />
        ตัวกรองเพิ่มเติม
        {activeCount > 0 && <span className="small-count">{activeCount}</span>}
      </Button>
    </>
  );
  const search = (
    <GetSearch
      className="company-search"
      aria-label="ค้นหาเคส"
      placeholder="ค้นหาเลขเคส หัวข้อ หรือชื่อลูกค้า"
      value={query}
      onChange={(next) => {
        setQuery(next);
        reset();
      }}
    />
  );
  const chips: { key: string; label: string; remove: () => void }[] = [
    ...filters.statuses.map((value) => ({
      key: `s-${value}`,
      label: statusNames[value] || value,
      remove: () => apply({ ...filters, statuses: filters.statuses.filter((v) => v !== value) }),
    })),
    ...filters.products.map((value) => ({
      key: `p-${value}`,
      label: data?.products.find((p) => p.code === value)?.name || value,
      remove: () => apply({ ...filters, products: [] }),
    })),
    ...filters.priorities.map((value) => ({
      key: `r-${value}`,
      label: `${value} ${severityNames[value] || ""}`,
      remove: () => apply({ ...filters, priorities: filters.priorities.filter((v) => v !== value) }),
    })),
  ];

  return (
    <AppShell
      title={title}
      counts={data ? { mine: data.summary.mine, unassigned: data.summary.unassigned } : undefined}
    >
      <div className={cx("queue-page", view === "all" && "all-cases-page")}>
        <div className="page-heading">
          <div>
            <h1>
              {title}
              {view === "work" && !product && (
                <span className="heading-date">
                  {now.toLocaleDateString("th-TH", {
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
                ? "ค้นหาและเปิดดูเคสทุกสถานะที่คุณมีสิทธิ์เห็น"
                : view === "unassigned"
                  ? "เคสใหม่ที่ยังไม่มีใครรับ เลือกเคสเพื่อรับไปดำเนินการ"
                  : "เคสที่เปิดอยู่ เรียงจากเคสที่ใกล้ครบกำหนด SLA ก่อน"}
            </p>
          </div>
          <div className="heading-actions">
            <span className="last-updated" aria-live="polite">
              <span className="healthy-dot" />
              อัปเดต{" "}
              {updated?.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" }) ||
                "—"}{" "}
              น.
              <Button
                variant="ghost"
                size="icon"
                aria-label="โหลดรายการใหม่"
                onClick={() => load()}
              >
                <RefreshCw size={13} className={cx(loading && "animate-spin")} />
              </Button>
            </span>
            {view === "all" && session && EXPORT_ROLES.has(session.role) && (
              <Link href={href("/cases/search")} className="button button-secondary">
                <SearchIcon size={15} />
                ค้นหาขั้นสูง / ส่งออก
              </Link>
            )}
            {(session?.can_open_cases ?? session?.can_create_cases) && (
              <Link href={href("/cases/new")} className="button button-primary">
                <Plus size={16} />
                สร้างเคส
              </Link>
            )}
          </div>
        </div>
        {view === "work" && !product && (
          <div className="action-counts">
            {(
              [
                [data?.summary.unassigned, "ยังไม่มีผู้รับเคส", "users", "unassigned", "unassigned"],
                [data?.summary.sla_at_risk, "ใกล้ครบกำหนดหรือเกิน SLA", "clock", "risk", "risk"],
                [data?.summary.mine, "งานที่ฉันดำเนินการอยู่", "user", "mine", "mine"],
                [data?.summary.today, "เคสเข้าใหม่วันนี้", "folder", "today", "incoming"],
              ] as const
            ).map(([count, label, icon, itemScope, style]) => (
              <button
                key={itemScope}
                className={`native-stat-action stat-${style}`}
                aria-pressed={scope === itemScope}
                onClick={() => changeScope(scope === itemScope ? "open" : itemScope)}
              >
                <StatCard
                  size="small"
                  label={label}
                  value={count ?? "—"}
                  icon
                  iconName={icon}
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
        <section className="surface queue-surface">
          <div className="queue-heading">
            <h2>{view === "all" ? "รายการเคส" : "เคสที่เปิดอยู่"}</h2>
            {view !== "unassigned" && (
              <Segment
                aria-label="มุมมองรายการ"
                value={scope}
                onChange={(next) => changeScope(next as Scope)}
                options={
                  view === "all"
                    ? [
                        { value: "open", label: "เปิดอยู่" },
                        { value: "all", label: "ทุกสถานะ" },
                        { value: "mine", label: "ของฉัน" },
                        { value: "unassigned", label: "ยังไม่มีผู้รับ" },
                      ]
                    : [
                        { value: "open", label: "ทั้งหมด" },
                        { value: "mine", label: "ของฉัน" },
                        { value: "team", label: "ทีมของฉัน" },
                        { value: "unassigned", label: "ยังไม่มีผู้รับ" },
                      ]
                }
              />
            )}
            <div className="queue-heading-actions">
              <label className="sort-control">
                เรียงตาม
                <SelectControl
                  aria-label="เรียงรายการเคส"
                  value={sort}
                  onValueChange={(next) => {
                    setSort(next);
                    reset();
                  }}
                >
                  <option value="sla">ใกล้ครบกำหนด SLA ก่อน</option>
                  <option value="newest">สร้างล่าสุดก่อน</option>
                  <option value="oldest">สร้างเก่าสุดก่อน</option>
                </SelectControl>
              </label>
            </div>
          </div>
          <div className="queue-toolbar">
            <div className="quick-filters">{quickFilters}</div>
            {search}
          </div>
          {(chips.length > 0 || activeCount > chips.length) && (
            <div className="applied-filters">
              <span>ตัวกรองที่ใช้ {activeCount} รายการ</span>
              {chips.map((chip) => (
                <button key={chip.key} onClick={chip.remove} aria-label={`เอาตัวกรอง ${chip.label} ออก`}>
                  {chip.label}
                  <X size={12} />
                </button>
              ))}
              <button className="clear-filters" onClick={() => apply({ ...emptyFilters })}>
                ล้างตัวกรองเพิ่มเติม
              </button>
            </div>
          )}
          {error ? (
            <ErrorState message={error} onRetry={load} />
          ) : !data ? (
            <TableSkeleton />
          ) : (
            <CaseTable
              rows={visibleRows}
              total={preview ? undefined : data.total}
              variant={view === "all" ? "all" : "work"}
              page={page}
              pageSize={pageSize}
              onPage={setPage}
              onPageSize={(size) => {
                setPageSize(size);
                reset();
              }}
              selected={selected}
              onSelected={setSelected}
              selectable={false}
            />
          )}
        </section>
        {withDrafts && data && <DraftList rows={data.drafts} onRefresh={load} />}
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
          slaAvailable
        />
      </div>
    </AppShell>
  );
}
