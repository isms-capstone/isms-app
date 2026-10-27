"use client";
import { Tag } from "@DeverhoodHT/get-design";
import {
  type LucideIcon,
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
  AlertTriangle,
  XCircle,
  Check,
  PlayCircle,
  FileEdit,
} from "lucide-react";
import type { CaseRow } from "@/lib/types";
import { channelNames, statusNames } from "@/lib/types";
import { cx } from "@/components/ui/primitives";

export function StatusBadge({
  status,
  compact = false,
}: {
  status: string | null;
  compact?: boolean;
}) {
  if (!status) return null;

  const currentStatus = status.toUpperCase();

  // กำหนดสไตล์ สี และไอคอนตาม Requirement BR-01..13
  const statusConfig: Record<
    string,
    {
      label: string;
      color: string;
      bg: string;
      border: string;
      icon: LucideIcon;
    }
  > = {
    DRAFT: {
      label: statusNames.DRAFT || "ร่าง",
      color: "#33454e",
      bg: "#76949f12",
      border: "#76949f40",
      icon: FileEdit,
    },
    NEW: {
      label: statusNames.NEW || "ใหม่",
      color: "#33454e",
      bg: "#76949f12",
      border: "#76949f40",
      icon: Clock3,
    },
    OPEN: {
      label: statusNames.OPEN || "เปิด",
      color: "#33454e",
      bg: "#76949f12",
      border: "#76949f40",
      icon: Clock3,
    },
    IN_PROGRESS: {
      label: statusNames.IN_PROGRESS || "กำลังดำเนินการ",
      color: "#33454e",
      bg: "#76949f12",
      border: "#76949f40",
      icon: PlayCircle,
    },
    PENDING: {
      label: statusNames.PENDING || "รอดำเนินการ",
      color: "#33454e",
      bg: "#76949f12",
      border: "#76949f40",
      icon: Clock3,
    },
    ESCALATED: {
      label: statusNames.ESCALATED || "ส่งต่อผู้เชี่ยวชาญ",
      color: "#33454e",
      bg: "#76949f12",
      border: "#76949f40",
      icon: AlertTriangle,
    },
    RESOLVED: {
      label: statusNames.RESOLVED || "แก้ไขแล้ว",
      color: "#33454e",
      bg: "#76949f12",
      border: "#76949f40",
      icon: CheckCircle2,
    },
    CLOSED: {
      label: statusNames.CLOSED || "ปิดเคส",
      color: "#33454e",
      bg: "#76949f12",
      border: "#76949f40",
      icon: Check,
    },
    CANCELLED: {
      label: statusNames.CANCELLED || "ยกเลิก",
      color: "#33454e",
      bg: "#76949f12",
      border: "#76949f40",
      icon: XCircle,
    },
  };

  const config = statusConfig[currentStatus] || {
    label: statusNames[status] || status,
    color: "#33454e",
    bg: "#76949f12",
    border: "#76949f40",
    icon: Clock3,
  };

  const Icon = config.icon;

  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border transition-colors",
        compact && "px-2 py-0.5 text-[11px]",
      )}
      style={{
        color: config.color,
        backgroundColor: config.bg,
        borderColor: config.border,
      }}
    >
      <Icon size={compact ? 12 : 14} />
      <span>{config.label}</span>
    </span>
  );
}

export function PriorityBadge({
  value,
  compact = false,
}: {
  value: string | null;
  compact?: boolean;
}) {
  const label: Record<string, string> = {
    S1: "Critical",
    S2: "High",
    S3: "Medium",
    S4: "Low",
  };
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
      style={
        value === "S1"
          ? { color: "#33454e", borderColor: "#9e2a2b" }
          : undefined
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

export function SlaIndicator({ row }: { row: CaseRow }) {
  if (row.slaSeconds === null)
    return (
      <span className="sla-missing" title="Backend ยังไม่มีการคำนวณ SLA">
        ยังไม่มีข้อมูล
      </span>
    );
  const seconds = Math.abs(row.slaSeconds),
    minutes = Math.floor(seconds / 60),
    hours = Math.floor(minutes / 60),
    days = Math.floor(hours / 24);
  const value = days
    ? `${days} วัน`
    : hours
      ? `${hours} ชม. ${minutes % 60} น.`
      : `${String(minutes).padStart(2, "0")}:${String(Math.floor(seconds % 60)).padStart(2, "0")} น.`;
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
  return (
    <span className={`sla-indicator sla-${state}`}>
      <span>
        <Icon size={15} />
        <strong>
          {row.slaSeconds < 0 ? "-" : ""}
          {value}
        </strong>
      </span>
      <small>
        {state === "breached"
          ? "SLA breached"
          : state === "risk"
            ? "At risk"
            : "On track"}
      </small>
    </span>
  );
}

export function Assignee({ row }: { row: CaseRow }) {
  return (
    <span className={cx("assignee", !row.assignee_id && "unassigned")}>
      <span className="avatar">{row.assigneeInitials}</span>
      <span>
        {row.assigneeInitials !== "–" && (
          <strong>{row.assigneeInitials} </strong>
        )}
        {row.assignee}
      </span>
    </span>
  );
}
