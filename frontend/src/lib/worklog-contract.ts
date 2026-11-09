/** Wire contracts supported by the merged backend and the WRK/CAT backend. */
export type BackendContract = {
  worklogFormat: "canonical" | "legacy" | null;
  timeline: boolean;
  categorization: boolean;
  requestWorkflow: boolean;
};

type OpenApi = {
  paths?: Record<
    string,
    {
      post?: {
        requestBody?: {
          content?: Record<string, { schema?: { $ref?: string } }>;
        };
      };
    }
  >;
  components?: {
    schemas?: Record<string, { properties?: Record<string, unknown> }>;
  };
};

export function inspectBackendContract(document: OpenApi): BackendContract {
  const paths = document.paths || {};
  const schema =
    paths["/api/v1/tickets/{ticket_id}/worklogs"]?.post?.requestBody?.content?.[
      "application/json"
    ]?.schema;
  const name = schema?.$ref?.split("/").at(-1);
  const fields =
    (name && document.components?.schemas?.[name]?.properties) || {};
  return {
    worklogFormat:
      "kind" in fields && "body" in fields
        ? "canonical"
        : "message" in fields && "is_internal" in fields
          ? "legacy"
          : null,
    timeline: "/api/v1/tickets/{ticket_id}/timeline" in paths,
    categorization: "/api/v1/tickets/{ticket_id}/categorization" in paths,
    requestWorkflow: "/api/v1/tickets/{ticket_id}/request-workflow" in paths,
  };
}

export type WorklogInput = {
  kind: "internal_note" | "public_reply";
  body: string;
  channel: string | null;
};
const channels = new Set([
  "line_oa",
  "line_group",
  "line_personal",
  "portal",
  "email",
  "phone",
  "face_to_face",
  "other",
]);

export function parseWorklogInput(value: unknown): WorklogInput {
  if (!value || typeof value !== "object" || Array.isArray(value))
    throw new Error("ข้อมูลข้อความไม่ถูกต้อง");
  const data = value as Record<string, unknown>;
  if (
    Object.keys(data).some((key) => !["kind", "body", "channel"].includes(key))
  )
    throw new Error("มีช่องข้อมูลข้อความที่ไม่รองรับ");
  if (data.kind !== "internal_note" && data.kind !== "public_reply")
    throw new Error("เลือกประเภทข้อความให้ถูกต้อง");
  if (
    typeof data.body !== "string" ||
    !data.body.trim() ||
    [...data.body].length > 20000
  )
    throw new Error("ข้อความต้องมี 1–20,000 ตัวอักษร");
  const channel = data.channel ?? null;
  if (
    data.kind === "public_reply" &&
    (typeof channel !== "string" || !channels.has(channel))
  )
    throw new Error("เลือกช่องทางที่ส่งจริงสำหรับ Public Reply");
  if (data.kind === "internal_note" && channel !== null)
    throw new Error("Internal Note ต้องไม่มีช่องทางภายนอก");
  return {
    kind: data.kind,
    body: data.body.trim(),
    channel: channel as string | null,
  };
}

export function encodeWorklog(
  input: WorklogInput,
  format: BackendContract["worklogFormat"],
) {
  if (format === "legacy")
    return {
      message: input.body,
      is_internal: input.kind === "internal_note",
      channel: input.channel,
    };
  if (format === "canonical") return input;
  throw new Error("Backend ยังไม่รองรับการบันทึกข้อความ");
}

export type WorklogRecord = {
  id: number;
  ticket_id: number;
  kind: "internal_note" | "public_reply";
  body: string;
  channel: string | null;
  actor_id: number;
  actor: string;
  created_at: string;
};

export function normalizeWorklog(
  row: Record<string, unknown>,
  format: BackendContract["worklogFormat"],
): WorklogRecord {
  const kind =
    format === "legacy"
      ? row.is_internal
        ? "internal_note"
        : "public_reply"
      : row.kind;
  const actorId = Number(format === "legacy" ? row.author_id : row.actor_id);
  const timestamp = String(row.created_at);
  return {
    id: Number(row.id),
    ticket_id: Number(row.ticket_id),
    kind: kind as WorklogRecord["kind"],
    body: String(format === "legacy" ? row.message : row.body),
    // Older backends default internal notes to the intake channel. Never present that as an external delivery.
    channel: kind === "internal_note" ? null : (row.channel as string | null),
    actor_id: actorId,
    actor: typeof row.actor === "string" ? row.actor : `ผู้ใช้ #${actorId}`,
    created_at: /(?:Z|[+-]\d{2}:\d{2})$/i.test(timestamp)
      ? timestamp
      : `${timestamp}Z`,
  };
}
