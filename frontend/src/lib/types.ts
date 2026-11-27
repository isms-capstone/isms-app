export type Session = {
  id: number;
  username: string;
  role: string;
  can_create_cases: boolean;
  /** SRS 3.2: Developer works cases but does not open new ones. */
  can_open_cases?: boolean;
  can_view_audit?: boolean;
  can_edit_customers: boolean;
  can_edit_products: boolean;
};
export type Product = {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
  modules: { id: number; name: string }[];
};
export type Organization = { id: number; name: string; is_active: boolean };
export type CustomerChoice = {
  organization: Organization;
  contact: { id: number; name: string } | null;
};
export type Instance = {
  id: number;
  name: string;
  product_id: number;
  version: string;
  environment: string;
};
export type SelectionContext = {
  organization: Organization;
  contact: { id: number; name: string } | null;
  instances: Instance[];
  departments: { id: number; name: string }[];
  courses: { id: number; name: string }[];
};
export type Ticket = {
  id: number;
  ticket_no: string | null;
  subject: string | null;
  description: string | null;
  status: string;
  organization_id: number | null;
  contact_id: number | null;
  product_instance_id: number | null;
  department_id: number | null;
  course_or_exam_id: number | null;
  module_id: number | null;
  category_id: number | null;
  symptom_id: number | null;
  service_stage_id: number | null;
  ticket_type_id: number | null;
  created_by_id: number;
  assignee_id: number | null;
  owner_id: number | null;
  channel: string | null;
  severity: string | null;
  current_tier: number | null;
  created_at: string;
  reported_at: string;
  resolved_at?: string | null;
  root_cause_code_id?: number | null;
  resolution_code_id?: number | null;
  resolution_detail?: string | null;
  sla_policy_id: number | null;
  sla_breached?: boolean;
  sla_breach_reason?: string | null;
  pending_customer_reason?: string | null;
  sla?: {
    first_response: SlaMetric;
    resolution: SlaMetric;
    paused: boolean;
    breached: boolean;
    remaining_seconds: number | null;
    remaining_ratio: number | null;
  } | null;
  source_url?: string | null;
  browser_device?: string | null;
  exam_or_course_context?: string | null;
  is_exam_window: boolean;
};
export type CaseRow = Ticket & {
  customer: string;
  customerType?: string;
  product: string;
  productId?: number;
  assignee: string;
  assigneeInitials: string;
  slaSeconds: number | null;
  slaRatio: number | null;
  slaPaused?: boolean;
  slaDueAt?: string | null;
  teamName?: string | null;
  typeName?: string;
};
/** One row of GET /case-queue (filtered, ordered and paged by the server). */
export type QueueRow = {
  id: number;
  ticket_no: string | null;
  subject: string | null;
  status: string;
  severity: string | null;
  channel: string | null;
  current_tier: number | null;
  created_at: string;
  reported_at: string | null;
  organization_id: number | null;
  customer: string | null;
  product_id: number | null;
  product: string | null;
  assignee_id: number | null;
  assignee: string | null;
  owner_id: number | null;
  team?: string | null;
  sla: {
    remaining_seconds: number | null;
    remaining_ratio: number | null;
    paused: boolean;
    breached: boolean;
    due_at: string | null;
  } | null;
};
export type QueuePage = { items: QueueRow[]; total: number };
export type Summary = {
  unassigned: number;
  mine: number;
  today: number;
  drafts: number;
  sla_at_risk: number | null;
};
export type QueueData = {
  rows: CaseRow[];
  total: number;
  drafts: CaseRow[];
  products: Product[];
  summary: Summary;
};
export const channelNames: Record<string, string> = {
  line_oa: "LINE OA",
  line_group: "LINE Group",
  line_personal: "LINE ส่วนตัว",
  portal: "พอร์ทัลลูกค้า",
  phone: "โทรศัพท์",
  email: "อีเมล",
  face_to_face: "พบหน้า",
  other: "อื่น ๆ",
};
/** Status names follow SRS section 7.1. */
export const statusNames: Record<string, string> = {
  DRAFT: "ร่าง",
  NEW: "ใหม่",
  IN_PROGRESS: "กำลังดำเนินการ",
  PENDING_CUSTOMER: "รอลูกค้า",
  PENDING_EXTERNAL: "รอทีมพัฒนา/ภายนอก",
  RESOLVED: "แก้ไขแล้ว",
  CLOSED: "ปิดแล้ว",
  REOPENED: "เปิดใหม่",
  DUPLICATE: "ซ้ำ",
  CANCELLED: "ยกเลิก",
};
/** Must match OPEN_STATUSES in backend/app/db/models/ticket.py. */
export const openStatuses = [
  "NEW",
  "IN_PROGRESS",
  "PENDING_CUSTOMER",
  "PENDING_EXTERNAL",
  "REOPENED",
];
export const severityNames: Record<string, string> = {
  S1: "วิกฤต",
  S2: "สูง",
  S3: "ปานกลาง",
  S4: "ต่ำ",
};
export const tierNames: Record<string, string> = {
  "2": "Tier 2 · หน้าด่าน",
  "1": "Tier 1 · ผู้เชี่ยวชาญ",
  "0": "Tier 0 · ทีมพัฒนา",
};

export type SlaMetric = {
  target_seconds: number;
  elapsed_seconds: number;
  remaining_seconds: number;
  finished: boolean;
  breached: boolean;
};
