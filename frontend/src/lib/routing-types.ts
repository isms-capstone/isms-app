export type RoutingUser = {
  id: number;
  name: string;
  team_id: number | null;
  default_tier: number;
  is_available: boolean;
  is_active: boolean;
  role: string;
};
export type RoutingOptions = {
  users: RoutingUser[];
  teams: { id: number; name: string }[];
  products: { id: number; name: string }[];
  calendars: { id: number; name: string }[];
  routes: { product_id: number; tier: number; team_id: number }[];
};
export type RoutingState = {
  ticket_id: number;
  tier: number;
  version: number;
  owner: { id: number; name: string } | null;
  assignee: { id: number; name: string } | null;
  first_response_at: string | null;
  seconds_by_tier: Record<string, number>;
  eligible_users: RoutingUser[];
  permissions: Record<string, boolean>;
  return_event_id: number | null;
  intervals: {
    tier: number;
    entered_at: string;
    exited_at: string | null;
    is_estimated: boolean;
  }[];
  events: {
    id: number;
    kind: string;
    actor: { name: string } | null;
    from_user: { name: string } | null;
    to_user: { name: string } | null;
    from_tier: number;
    to_tier: number;
    reason: string;
    checked: string | null;
    requested: string | null;
    created_at: string;
  }[];
};
export const routingNames: Record<string, string> = {
  handoff: "ส่งต่อเคส",
  auto_escalate: "ส่งต่ออัตโนมัติ",
  return: "ส่งคืนเคส",
  assign: "มอบหมายงาน",
  self_assign: "รับเคสด้วยตนเอง",
  bulk_handover: "ส่งมอบงานทั้งหมด",
  response: "รับทราบเคส",
};
export function routingDate(value: string) {
  return new Date(value.endsWith("Z") ? value : `${value}Z`).toLocaleString(
    "th-TH",
    { dateStyle: "medium", timeStyle: "short" },
  );
}
export function duration(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  return minutes < 60
    ? `${minutes} นาที`
    : `${Math.floor(minutes / 60)} ชม. ${minutes % 60} นาที`;
}
