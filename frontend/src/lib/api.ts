import type {
  CaseRow,
  Instance,
  Organization,
  Product,
  QueueData,
  Session,
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
      ...(init.body ? { "Content-Type": "application/json" } : {}),
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
export async function all<T>(path: string, signal?: AbortSignal): Promise<T[]> {
  const rows: T[] = [];
  for (let offset = 0; ; offset += 100) {
    const page = await api<T[]>(
      `${path}${path.includes("?") ? "&" : "?"}offset=${offset}&limit=100`,
      { signal },
    );
    rows.push(...page);
    if (page.length < 100) return rows;
  }
}
export async function queueData(
  session: Session,
  signal: AbortSignal,
): Promise<QueueData> {
  const [tickets, drafts, products, summary] = await Promise.all([
    all<Ticket>("/tickets", signal),
    all<Ticket>("/tickets?drafts_only=true", signal),
    all<Product>("/products?is_active=true", signal),
    api<Summary>("/tickets/queue-summary", { signal }),
  ]);
  const allTickets = [...tickets, ...drafts];
  const orgs = new Map(
    await Promise.all(
      [
        ...new Set(
          allTickets
            .map((t) => t.organization_id)
            .filter((id): id is number => id !== null),
        ),
      ].map(
        async (id) =>
          [
            id,
            await api<Organization>(`/customers/organizations/${id}`, {
              signal,
            }),
          ] as const,
      ),
    ),
  );
  const instances = new Map(
    await Promise.all(
      [
        ...new Set(
          allTickets
            .map((t) => t.product_instance_id)
            .filter((id): id is number => id !== null),
        ),
      ].map(
        async (id) =>
          [
            id,
            await api<Instance>(`/product-instances/${id}`, { signal }),
          ] as const,
      ),
    ),
  );
  const adapt = (ticket: Ticket): CaseRow => {
    const instance = instances.get(ticket.product_instance_id ?? -1);
    return {
      ...ticket,
      customer:
        orgs.get(ticket.organization_id ?? -1)?.name ?? "ยังไม่ระบุลูกค้า",
      product:
        products.find((p) => p.id === instance?.product_id)?.name ??
        "ยังไม่ระบุ",
      productId: instance?.product_id,
      assignee:
        ticket.assignee_id === session.id
          ? session.username
          : ticket.assignee_id
            ? `ผู้ใช้ #${ticket.assignee_id}`
            : "ยังไม่มีผู้รับ",
      assigneeInitials:
        ticket.assignee_id === session.id
          ? session.username.slice(0, 2).toUpperCase()
          : ticket.assignee_id
            ? "•"
            : "–",
      slaSeconds: null,
      slaRatio: null,
    };
  };
  return {
    rows: tickets.map(adapt),
    drafts: drafts.map(adapt),
    products,
    summary,
  };
}
