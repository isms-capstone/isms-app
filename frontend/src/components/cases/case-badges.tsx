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
  RotateCcw,
  Hourglass,
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
      color: "#64748b",
      bg: "#f1f5f9",
      border: "#cbd5e1",
      icon: FileEdit,
    },
    NEW: {
      label: statusNames.NEW || "ใหม่",
      color: "#0369a1",
      bg: "#e0f2fe",
      border: "#7dd3fc",
      icon: Clock3,
    },
    OPEN: {
      label: statusNames.OPEN || "เปิด",
      color: "#4338ca",
      bg: "#eef2ff",
      border: "#a5b4fc",
      icon: Clock3,
    },
    IN_PROGRESS: {
      label: statusNames.IN_PROGRESS || "กำลังดำเนินการ",
      color: "#1d4ed8",
      bg: "#dbeafe",
      border: "#93c5fd",
      icon: PlayCircle,
    },
    PENDING: {
      label: statusNames.PENDING || "รอดำเนินการ",
      color: "#b45309",
      bg: "#fef3c7",
      border: "#fcd34d",
      icon: Clock3,
    },
    // เพิ่ม: สถานะจริงของระบบคือ PENDING_CUSTOMER / PENDING_EXTERNAL ไม่ใช่ PENDING เฉยๆ
    // เดิมไม่มี key นี้ เลยตกไปใช้สีเทา fallback ทั้งที่ backend ส่งค่านี้มาจริง
    PENDING_CUSTOMER: {
      label: statusNames.PENDING_CUSTOMER || "รอลูกค้าตอบกลับ",
      color: "#b45309",
      bg: "#fef3c7",
      border: "#fcd34d",
      icon: Hourglass,
    },
    PENDING_EXTERNAL: {
      label: statusNames.PENDING_EXTERNAL || "รอหน่วยงานภายนอก",
      color: "#7e22ce",
      bg: "#f3e8ff",
      border: "#d8b4fe",
      icon: Hourglass,
    },
    ESCALATED: {
      label: statusNames.ESCALATED || "ส่งต่อผู้เชี่ยวชาญ",
      color: "#c2410c",
      bg: "#ffedd5",
      border: "#fdba74",
      icon: AlertTriangle,
    },
    RESOLVED: {
      label: statusNames.RESOLVED || "แก้ไขแล้ว",
      color: "#15803d",
      bg: "#dcfce7",
      border: "#86efac",
      icon: CheckCircle2,
    },
    CLOSED: {
      label: statusNames.CLOSED || "ปิดเคส",
      color: "#475569",
      bg: "#f1f5f9",
      border: "#cbd5e1",
      icon: Check,
    },
    // เพิ่ม: REOPENED เดิมไม่มี key นี้เลยตกไปใช้สีเทา fallback
    REOPENED: {
      label: statusNames.REOPENED || "เปิดใหม่อีกครั้ง",
      color: "#a16207",
      bg: "#fef9c3",
      border: "#fde047",
      icon: RotateCcw,
    },
    CANCELLED: {
      label: statusNames.CANCELLED || "ยกเลิก",
      color: "#b91c1c",
      bg: "#fee2e2",
      border: "#fca5a5",
      icon: XCircle,
    },
    DUPLICATE: {
      label: statusNames.DUPLICATE || "เคสซ้ำ",
      color: "#7e22ce",
      bg: "#f3e8ff",
      border: "#d8b4fe",
      icon: AlertTriangle,
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
  "inline-flex items-center whitespace-nowrap rounded-full border font-semibold leading-none transition-colors",
  compact ? "gap-1 px-2 py-0.5 text-[11px]" : "gap-1.5 px-2.5 py-1 text-xs",
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