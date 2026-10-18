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
import { channelNames } from "@/lib/types";
import { cx } from "@/components/ui/primitives";
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
    <span
      className={cx(
        "priority-pill",
        `priority-${value || "unknown"}`,
        compact && "compact",
      )}
    >
      {value
        ? `${value}${compact ? "" : ` ${label[value] || ""}`}`
        : "ยังไม่ระบุ"}
    </span>
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
