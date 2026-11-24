"use client";
import { formatShortDate } from "@/lib/format";
import { SelectControl } from "@/components/ui/company-fields";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, ArrowUpRight } from "lucide-react";
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
  StatusBadge,
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
  total,
  selectable = true,
}: {
  rows: CaseRow[];
  /** Hide the checkbox column when the page offers no bulk action. */
  selectable?: boolean;
  /** When set, `rows` is already the current server page out of `total`. */
  total?: number;
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
  const count = total ?? rows.length,
    pages = Math.max(1, Math.ceil(count / pageSize)),
    current = Math.min(page, pages),
    visible =
      total === undefined
        ? rows.slice((current - 1) * pageSize, current * pageSize)
        : rows;
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
          "เลขเคส",
          "หัวข้อ",
          "ลูกค้า",
          "ผลิตภัณฑ์",
          "ความรุนแรง",
          "สถานะ",
          "ช่องทาง",
          "ผู้ดำเนินการ",
          "SLA",
        ]
      : [
          "เคส / หัวข้อ",
          "ลูกค้า",
          "สถานะ",
          "ความรุนแรง",
          "ผลิตภัณฑ์",
          "ช่องทาง",
          "Tier",
          "SLA",
          "ผู้ดำเนินการ",
        ];
  return (
    <>
      <div className="case-table-scroll">
        <table
          className={cx("case-table", variant === "all" && "all-cases-table")}
        >
          <thead>
            <tr>
              {selectable && <TableHeaderCell className="selection-col">
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
              </TableHeaderCell>}
              {columns.map((column) => (
                <TableHeaderCell
                  key={column}
                  className={column === "ช่องทาง" ? "channel-col" : undefined}
                >
                  {column}
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
                {selectable && (
                  <TableCell className="selection-col">
                    <Checkbox
                      aria-label={`เลือกเคส ${row.ticket_no || row.id}`}
                      checked={selected.has(row.id)}
                      onChange={() => toggle(row.id)}
                    />
                  </TableCell>
                )}
                {variant === "all" ? (
                  <>
                    <TableCell className="case-number-cell">
                      <Link href={href(`/cases/${row.id}`)}>
                        {row.ticket_no || `ร่าง #${row.id}`}
                      </Link>
                      <small>
                        {formatShortDate(row.created_at)}
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
                    <TableCell data-label="ความรุนแรง">
                      <PriorityBadge value={row.severity} compact />
                    </TableCell>
                    <TableCell data-label="สถานะ">
                      <StatusBadge status={row.status} compact />
                    </TableCell>
                    <TableCell data-label="ช่องทาง" className="channel-col">
                      <ChannelLabel channel={row.channel} />
                    </TableCell>
                    <TableCell data-label="ผู้ดำเนินการ">
                      <Assignee row={row} />
                    </TableCell>
                    <TableCell data-label="SLA">
                      <SlaIndicator row={row} />
                    </TableCell>
                  </>
                ) : (
                  <>
                    <TableCell data-label="สถานะ">
                      <StatusBadge status={row.status} compact />
                    </TableCell>
                    <TableCell data-label="ความรุนแรง">
                      <PriorityBadge value={row.severity} />
                    </TableCell>
                    <TableCell data-label="ผลิตภัณฑ์">
                      <ProductLabel name={row.product} />
                    </TableCell>
                    <TableCell data-label="ช่องทาง" className="channel-col">
                      <ChannelLabel channel={row.channel} />
                    </TableCell>
                    <TableCell data-label="Tier">
                      <span className="tier-label">
                        {row.current_tier === null ? "—" : `Tier ${row.current_tier}`}
                      </span>
                    </TableCell>
                    <TableCell data-label="SLA">
                      <SlaIndicator row={row} />
                    </TableCell>
                    <TableCell data-label="ผู้ดำเนินการ">
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
                </TableCell>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!rows.length && (
        <EmptyState
          title="ไม่พบเคสตามเงื่อนไขนี้"
          description="ลองล้างตัวกรองหรือเปลี่ยนคำค้นหา"
        />
      )}
      <footer className="table-pagination">
        <span>
          แสดง {count ? (current - 1) * pageSize + 1 : 0}–
          {Math.min(current * pageSize, count)} จาก{" "}
          {count.toLocaleString("th-TH")} เคส
        </span>
        <div>
          <label>
            ต่อหน้า
            <SelectControl
              aria-label="จำนวนเคสต่อหน้า"
              value={pageSize}
              onValueChange={(nextValue) => {
                onPageSize(Number(nextValue));
                onPage(1);
              }}
            >
              {[10, 25, 50].map((n) => (
                <option key={n}>{n}</option>
              ))}
            </SelectControl>
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