"use client";
import { Tag } from "@DeverhoodHT/get-design";
import {
  AlarmClock,
  Clock3,
  CheckCircle2,
  BookOpen,
  MonitorCog,
  ShieldCheck,
  Phone,
  Globe,
  Mail,
  MessageCircle,
  Users,
} from "lucide-react";
import type { CaseRow } from "@/lib/types";
import { channelNames, severityNames, statusNames } from "@/lib/types";
import { cx } from "@/components/ui/primitives";
import { formatDateTime, formatDuration } from "@/lib/format";

export function StatusBadge({
  status,
  compact = false,
}: {
  status: string | null;
  compact?: boolean;
}) {
  if (!status) return null;

  const currentStatus = status.toUpperCase();

  const tone =
    currentStatus === "RESOLVED"
      ? "success"
      : ["CANCELLED", "DUPLICATE"].includes(currentStatus)
        ? "danger"
        : currentStatus.startsWith("PENDING")
          ? "warning"
          : ["IN_PROGRESS", "REOPENED"].includes(currentStatus)
            ? "brand"
            : "neutral";
  return (
    <Tag
      variant="soft"
      className={cx("case-status", compact && "case-status-compact")}
      data-status={currentStatus}
      data-tone={tone}
      label={statusNames[currentStatus] || currentStatus}
    />
  );
}

export function PriorityBadge({
  value,
  compact = false,
}: {
  value: string | null;
  compact?: boolean;
}) {
  const label = severityNames;
  return (
    <Tag
      className="case-priority"
      data-priority={value || "unknown"}
      variant="outline"
      label={
        value
          ? `${value}${compact ? "" : ` ${label[value] || ""}`}`
          : "ยังไม่ระบุ"
      }
    />
  );
}

export function ProductLabel({ name }: { name: string }) {
  const Icon =
    name === "Logbook" ? BookOpen : name === "GetA" ? ShieldCheck : MonitorCog;
  return (
    <span className="product-label">
      <Icon size={16} />
      {name}
    </span>
  );
}

export function ChannelLabel({ channel }: { channel: string | null }) {
  const line = channel?.startsWith("line");
  const Icon = line
    ? MessageCircle
    : channel === "phone"
      ? Phone
      : channel === "email"
        ? Mail
        : channel === "face_to_face"
          ? Users
          : Globe;
  return (
    <span className="channel-label">
      <span className={cx("channel-icon", line && "channel-line")}>
        <Icon size={14} />
      </span>
      {channelNames[channel || ""] || "ยังไม่ระบุ"}
    </span>
  );
}

/** Remaining SLA time. S2-S4 count business hours only, S1 counts 24x7. */
export function SlaIndicator({ row }: { row: CaseRow }) {
  if (row.slaPaused)
    return (
      <span className="sla-indicator sla-paused" title="หยุดนับเวลาระหว่างรอลูกค้า">
        <span>
          <Clock3 size={15} />
          <strong>หยุดนับ</strong>
        </span>
        <small>รอลูกค้า</small>
      </span>
    );
  if (row.slaSeconds === null)
    return (
      <span className="sla-missing" title="เคสนี้ยังไม่มีเป้าหมาย SLA (ยังไม่ระบุความรุนแรง หรือปิดแล้ว)">
        —
      </span>
    );
  const state =
    row.slaSeconds < 0
      ? "breached"
      : row.slaRatio !== null && row.slaRatio < 0.25
        ? "risk"
        : "safe";
  const Icon =
    state === "breached"
      ? AlarmClock
      : state === "risk"
        ? Clock3
        : CheckCircle2;
  const due = row.slaDueAt ? formatDateTime(row.slaDueAt) : undefined;
  return (
    <span
      className={`sla-indicator sla-${state}`}
      title={due ? `ครบกำหนด ${due} น.` : undefined}
    >
      <span>
        <Icon size={15} />
        <strong>
          {state === "breached"
            ? `เกิน ${formatDuration(row.slaSeconds)}`
            : `เหลือ ${formatDuration(row.slaSeconds)}`}
        </strong>
      </span>
      <small>
        {state === "breached"
          ? "เกิน SLA"
          : state === "risk"
            ? "ใกล้ครบกำหนด"
            : "ทันเวลา"}
      </small>
    </span>
  );
}

export function Assignee({ row }: { row: CaseRow }) {
  return (
    <span className={cx("assignee", !row.assignee_id && "unassigned")}>
      <span className="avatar">{row.assigneeInitials}</span>
      <span>{row.assignee}</span>
    </span>
  );
}
