export type Session = {
  id: number;
  username: string;
  role: string;
  can_create_cases: boolean;
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
  sla_policy_id: number | null;
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
  typeName?: string;
};
export type Summary = {
  unassigned: number;
  mine: number;
  today: number;
  drafts: number;
  sla_at_risk: number | null;
};
export type QueueData = {
  rows: CaseRow[];
  drafts: CaseRow[];
  products: Product[];
  summary: Summary;
};
export const channelNames: Record<string, string> = {
  line_oa: "LINE OA",
  line_group: "LINE Group",
  line_personal: "LINE ส่วนตัว",
  portal: "แจ้งในระบบ",
  phone: "โทรศัพท์",
  email: "อีเมล",
  face_to_face: "พบหน้า",
  other: "อื่น ๆ",
};
export const statusNames: Record<string, string> = {
  NEW: "New",
  IN_PROGRESS: "In Progress",
  PENDING_CUSTOMER: "Pending Customer",
  RESOLVED: "Resolved",
  CLOSED: "Closed",
  REOPENED: "Reopened",
  DUPLICATE: "Duplicate",
  CANCELLED: "Cancelled",
  DRAFT: "Draft",
};
export const openStatuses = [
  "NEW",
  "IN_PROGRESS",
  "PENDING_CUSTOMER",
  "REOPENED",
];
