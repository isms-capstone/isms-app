"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ChevronLeft,
  ChevronRight,
  MoreVertical,
  ArrowUpDown,
  ArrowUpRight,
} from "lucide-react";
import { useSession } from "@/components/providers/session-provider";
import {
  Button,
  EmptyState,
  cx,
  TableCell,
  TableHeaderCell,
  Checkbox,
} from "@/components/ui/primitives";
import type { CaseRow } from "@/lib/types";
import {
  Assignee,
  ChannelLabel,
  PriorityBadge,
  ProductLabel,
  SlaIndicator,
} from "./case-badges";
export function CaseTable({
  rows,
  variant = "work",
  page,
  pageSize,
  onPage,
  onPageSize,
  selected,
  onSelected,
}: {
  rows: CaseRow[];
  variant?: "work" | "all";
  page: number;
  pageSize: number;
  onPage: (value: number) => void;
  onPageSize: (value: number) => void;
  selected: Set<number>;
  onSelected: (value: Set<number>) => void;
}) {
  const { href } = useSession();
  const router = useRouter();
  const pages = Math.max(1, Math.ceil(rows.length / pageSize)),
    current = Math.min(page, pages),
    visible = rows.slice((current - 1) * pageSize, current * pageSize);
  const toggle = (id: number) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelected(next);
  };
  const allSelected =
    visible.length > 0 && visible.every((row) => selected.has(row.id));
  const columns =
    variant === "all"
      ? [
          "CASE",
          "SUBJECT",
          "CUSTOMER",
          "PRODUCT",
          "TYPE",
          "PRIORITY",
          "STATUS",
          "CHANNEL",
          "ASSIGNEE",
          "SLA",
        ]
      : [
          "CASE / SUBJECT",
          "CUSTOMER",
          "PRIORITY",
          "PRODUCT",
          "CHANNEL",
          "TIER",
          "SLA",
          "ASSIGNEE",
        ];
  return (
    <>
      <div className="case-table-scroll">
        <table
          className={cx("case-table", variant === "all" && "all-cases-table")}
        >
          <thead>
            <tr>
              <TableHeaderCell className="selection-col">
                <Checkbox
                  aria-label="เลือกเคสในหน้านี้ทั้งหมด"
                  checked={allSelected}
                  onChange={() => {
                    const next = new Set(selected);
                    visible.forEach((row) =>
                      allSelected ? next.delete(row.id) : next.add(row.id),
                    );
                    onSelected(next);
                  }}
                />
              </TableHeaderCell>
              {columns.map((column) => (
                <TableHeaderCell key={column}>
                  {column}
                  {variant === "all" && (
                    <ArrowUpDown size={10} aria-hidden="true" />
                  )}
                </TableHeaderCell>
              ))}
              <TableHeaderCell className="row-action-col">
                <span className="sr-only">เปิดเคส</span>
              </TableHeaderCell>
            </tr>
          </thead>
          <tbody>
            {visible.map((row) => (
              <tr
                key={row.id}
                className={cx(selected.has(row.id) && "selected-row")}
                onClick={(event) => {
                  if (
                    !(event.target as HTMLElement).closest(
                      "a,button,input,label",
                    )
                  )
                    router.push(href(`/cases/${row.id}`));
                }}
              >
                <TableCell className="selection-col">
                  <Checkbox
                    aria-label={`เลือกเคส ${row.ticket_no || row.id}`}
                    checked={selected.has(row.id)}
                    onChange={() => toggle(row.id)}
                  />
                </TableCell>
                {variant === "all" ? (
                  <>
                    <TableCell className="case-number-cell">
                      <Link href={href(`/cases/${row.id}`)}>
                        {row.ticket_no || `ร่าง #${row.id}`}
                      </Link>
                      <small>
                        {new Date(row.created_at).toLocaleDateString("th-TH", {
                          day: "numeric",
                          month: "short",
                          timeZone: "Asia/Bangkok",
                        })}
                      </small>
                    </TableCell>
                    <TableCell className="subject-only">
                      <Link href={href(`/cases/${row.id}`)}>
                        {row.subject || "ยังไม่มีหัวข้อ"}
                      </Link>
                    </TableCell>
                  </>
                ) : (
                  <TableCell className="case-subject-cell">
                    <Link href={href(`/cases/${row.id}`)}>
                      <small>{row.ticket_no || `ร่าง #${row.id}`}</small>
                      <strong>{row.subject || "ยังไม่มีหัวข้อ"}</strong>
                    </Link>
                  </TableCell>
                )}
                <TableCell data-label="ลูกค้า" className="customer-cell">
                  <span>{row.customer}</span>
                  {row.customerType && <small>{row.customerType}</small>}
                </TableCell>
                {variant === "all" ? (
                  <>
                    <TableCell data-label="ผลิตภัณฑ์">
                      <ProductLabel name={row.product} />
                    </TableCell>
                    <TableCell data-label="ประเภท" className="muted-cell">
                      {row.typeName || "—"}
                    </TableCell>
                    <TableCell data-label="Priority">
                      <PriorityBadge value={row.severity} compact />
                    </TableCell>
                    <TableCell data-label="สถานะ">
                      <span className={`status-label status-${row.status}`}>
                        {row.status.replaceAll("_", " ")}
                      </span>
                    </TableCell>
                    <TableCell data-label="ช่องทาง">
                      <ChannelLabel channel={row.channel} />
                    </TableCell>
                    <TableCell data-label="ผู้รับผิดชอบ">
                      <Assignee row={row} />
                    </TableCell>
                    <TableCell data-label="SLA">
                      <SlaIndicator row={row} />
                    </TableCell>
                  </>
                ) : (
                  <>
                    <TableCell data-label="Priority">
                      <PriorityBadge value={row.severity} />
                    </TableCell>
                    <TableCell data-label="ผลิตภัณฑ์">
                      <ProductLabel name={row.product} />
                    </TableCell>
                    <TableCell data-label="ช่องทาง">
                      <ChannelLabel channel={row.channel} />
                    </TableCell>
                    <TableCell data-label="Tier">
                      <span className="tier-label">
                        {row.current_tier === null ? (
                          "—"
                        ) : (
                          <>
                            Tier
                            <br />
                            {row.current_tier}
                          </>
                        )}
                      </span>
                    </TableCell>
                    <TableCell data-label="SLA">
                      <SlaIndicator row={row} />
                    </TableCell>
                    <TableCell data-label="ผู้รับผิดชอบ">
                      <Assignee row={row} />
                    </TableCell>
                  </>
                )}
                <TableCell className="row-action-col">
                  <Link
                    className="row-open"
                    aria-label={`เปิดเคส ${row.ticket_no || row.id}`}
                    href={href(`/cases/${row.id}`)}
                  >
                    <ArrowUpRight size={16} />
                  </Link>
                  <MoreVertical
                    className="row-more"
                    size={16}
                    aria-hidden="true"
                  />
                </TableCell>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!rows.length && (
        <EmptyState>
          <Link href={href("/cases")} className="button button-secondary">
            ดูเคสทั้งหมด
          </Link>
        </EmptyState>
      )}
      <footer className="table-pagination">
        <span>
          แสดง {rows.length ? (current - 1) * pageSize + 1 : 0} -{" "}
          {Math.min(current * pageSize, rows.length)} จาก{" "}
          {rows.length.toLocaleString("th-TH")} เคส
        </span>
        <div>
          <label>
            แสดงต่อหน้า:
            <select
              aria-label="จำนวนเคสต่อหน้า"
              value={pageSize}
              onChange={(e) => {
                onPageSize(Number(e.target.value));
                onPage(1);
              }}
            >
              {[10, 25, 50].map((n) => (
                <option key={n}>{n}</option>
              ))}
            </select>
          </label>
          <Button
            size="icon"
            aria-label="หน้าก่อนหน้า"
            disabled={current === 1}
            onClick={() => onPage(current - 1)}
          >
            <ChevronLeft size={16} />
          </Button>
          {Array.from({ length: Math.min(5, pages) }, (_, i) => {
            const n = Math.max(1, Math.min(current - 2, pages - 4)) + i;
            return (
              <Button
                key={n}
                className={cx(n === current && "current-page")}
                aria-current={n === current ? "page" : undefined}
                onClick={() => onPage(n)}
              >
                {n}
              </Button>
            );
          })}
          {pages > 5 && <span>… {pages}</span>}
          <Button
            size="icon"
            aria-label="หน้าถัดไป"
            disabled={current === pages}
            onClick={() => onPage(current + 1)}
          >
            <ChevronRight size={16} />
          </Button>
        </div>
      </footer>
    </>
  );
}
