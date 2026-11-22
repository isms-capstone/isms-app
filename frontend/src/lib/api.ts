import type {
  CaseRow,
  Product,
  QueueData,
  QueuePage,
  QueueRow,
  Summary,
  Ticket,
} from "./types";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/backend${path}`, {
    ...init,
   headers: {
  ...(init.body && !(init.body instanceof FormData)
    ? { "Content-Type": "application/json" } : {}),
  ...init.headers,
},
    cache: "no-store",
  });
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined")
      window.dispatchEvent(new Event("isms:unauthorized"));
    const message =
      typeof data?.detail === "string"
        ? data.detail
        : Array.isArray(data?.detail)
          ? data.detail.map((item: { msg: string }) => item.msg).join(" · ")
          : "ไม่สามารถเชื่อมต่อระบบได้";
    throw new ApiError(message, response.status);
  }
  return data;
}
export async function all<T>(
  path: string,
  signal?: AbortSignal,
  offsetKey: "offset" | "skip" = "offset",
): Promise<T[]> {
  const rows: T[] = [];
  for (let offset = 0; ; offset += 100) {
    const page = await api<T[]>(
      `${path}${path.includes("?") ? "&" : "?"}${offsetKey}=${offset}&limit=100`,
      { signal },
    );
    rows.push(...page);
    if (page.length < 100) return rows;
  }
}
export type QueueQuery = {
  scope: string;
  product?: string;
  statuses: string[];
  severities: string[];
  tiers: string[];
  channels: string[];
  sla: string[];
  assignee: string;
  createdFrom?: string;
  createdTo?: string;
  q: string;
  sort: string;
  offset: number;
  limit: number;
};
function queueParams(query: QueueQuery) {
  const params = new URLSearchParams({
    scope: query.scope,
    sort: query.sort,
    assignee: query.assignee,
    offset: String(query.offset),
    limit: String(query.limit),
  });
  if (query.product) params.set("product", query.product);
  if (query.q.trim()) params.set("q", query.q.trim());
  if (query.createdFrom) params.set("created_from", query.createdFrom);
  if (query.createdTo) params.set("created_to", query.createdTo);
  for (const [key, values] of [
    ["status", query.statuses],
    ["severity", query.severities],
    ["tier", query.tiers],
    ["channel", query.channels],
    ["sla", query.sla],
  ] as const)
    values.forEach((value) => params.append(key, value));
  return params;
}
function initials(name: string | null) {
  if (!name) return "–";
  const parts = name.trim().split(/\s+/);
  return (parts.length > 1 ? parts[0][0] + parts[1][0] : name.slice(0, 2)).toUpperCase();
}
export function queueRow(row: QueueRow): CaseRow {
  return {
    ...(row as unknown as Ticket),
    customer: row.customer ?? "ยังไม่ระบุลูกค้า",
    product: row.product ?? "ยังไม่ระบุ",
    productId: row.product_id ?? undefined,
    assignee: row.assignee ?? "ยังไม่มีผู้รับ",
    assigneeInitials: initials(row.assignee),
    slaSeconds: row.sla?.remaining_seconds ?? null,
    slaRatio: row.sla?.remaining_ratio ?? null,
    slaPaused: row.sla?.paused ?? false,
    slaDueAt: row.sla?.due_at ?? null,
  };
}
/** One server-side page of the work queue plus the side data the screen needs. */
export async function queueData(
  query: QueueQuery,
  signal: AbortSignal,
  withDrafts: boolean,
): Promise<QueueData> {
  const [page, drafts, products, summary] = await Promise.all([
    api<QueuePage>(`/case-queue?${queueParams(query)}`, { signal }),
    withDrafts
      ? api<Ticket[]>("/tickets?drafts_only=true&limit=100", { signal })
      : Promise.resolve([] as Ticket[]),
    api<Product[]>("/products?is_active=true&limit=100", { signal }),
    api<Summary>("/tickets/queue-summary", { signal }),
  ]);
  const draftRow = (ticket: Ticket): CaseRow => ({
    ...ticket,
    customer: "",
    product: "",
    assignee: "",
    assigneeInitials: "",
    slaSeconds: null,
    slaRatio: null,
  });
  return {
    rows: page.items.map(queueRow),
    total: page.total,
    drafts: drafts.map(draftRow),
    products,
    summary,
  };
}

/** Resolve a case number such as DVHT-202611-00001 to its internal id. */
export async function findCaseByNumber(value: string): Promise<number> {
  const number = value.trim().toUpperCase();
  if (/^\d+$/.test(number)) return Number(number);
  const found = await api<QueuePage>(
    `/case-queue?scope=all&limit=5&q=${encodeURIComponent(number)}`,
  );
  const match = found.items.find((row) => row.ticket_no === number);
  if (!match) throw new Error(`ไม่พบเคสเลข ${number} กรุณาตรวจเลขเคสอีกครั้ง`);
  return match.id;
}
