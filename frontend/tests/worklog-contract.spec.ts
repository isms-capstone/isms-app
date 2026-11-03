import { test, expect } from "@playwright/test";
import { readBackendJson } from "../src/lib/backend-response";
import {
  inspectBackendContract,
  parseWorklogInput,
  encodeWorklog,
  normalizeWorklog,
} from "../src/lib/worklog-contract";

test("plain-text backend 500 stays a server error without leaking its traceback", async () => {
  const decoded = await readBackendJson(
    new Response("private database traceback", { status: 500 }),
  );
  expect(decoded.status).toBe(500);
  expect(decoded.data).toMatchObject({ code: "backend_error" });
  expect(JSON.stringify(decoded.data)).not.toContain(
    "private database traceback",
  );
  expect(JSON.stringify(decoded.data)).not.toContain("ไม่สามารถเชื่อมต่อ");
});

test("JSON permission errors are preserved and unconfirmed saves discourage duplicate retry", async () => {
  const forbidden = await readBackendJson(
    Response.json({ detail: "Forbidden" }, { status: 403 }),
  );
  expect(forbidden).toMatchObject({
    status: 403,
    data: { detail: "Forbidden" },
    validJson: true,
  });
  const unconfirmed = await readBackendJson(
    new Response("not JSON", { status: 201 }),
  );
  expect(unconfirmed).toMatchObject({
    status: 502,
    data: { code: "invalid_backend_response" },
  });
});

test("detect both worklog contracts without assuming missing endpoints exist", () => {
  for (const [format, properties] of [
    ["legacy", { message: {}, is_internal: {} }],
    ["canonical", { kind: {}, body: {} }],
  ] as const) {
    const contract = inspectBackendContract({
      paths: {
        "/api/v1/tickets/{ticket_id}/worklogs": {
          post: {
            requestBody: {
              content: {
                "application/json": {
                  schema: { $ref: "#/components/schemas/WorklogCreate" },
                },
              },
            },
          },
        },
      },
      components: { schemas: { WorklogCreate: { properties } } },
    });
    expect(contract.worklogFormat).toBe(format);
    expect(contract.timeline).toBe(false);
    expect(contract.categorization).toBe(false);
  }
  expect(inspectBackendContract({}).worklogFormat).toBeNull();
});

test("map canonical input to the observed message/is_internal schema", () => {
  const note = parseWorklogInput({
    kind: "internal_note",
    body: " ข้อมูลภายใน ",
    channel: null,
  });
  expect(encodeWorklog(note, "legacy")).toEqual({
    message: "ข้อมูลภายใน",
    is_internal: true,
    channel: null,
  });
  const reply = parseWorklogInput({
    kind: "public_reply",
    body: "แจ้งแล้ว",
    channel: "line_oa",
  });
  expect(encodeWorklog(reply, "legacy")).toEqual({
    message: "แจ้งแล้ว",
    is_internal: false,
    channel: "line_oa",
  });
  expect(encodeWorklog(reply, "canonical")).toEqual(reply);
});

test("normalize actual actor/time/channel without treating internal intake channel as delivery", () => {
  const row = {
    id: 1,
    ticket_id: 1,
    author_id: 20,
    message: "ข้อมูลภายใน",
    is_internal: true,
    channel: "phone",
    created_at: "2026-11-03T10:00:00",
  };
  expect(normalizeWorklog(row, "legacy")).toMatchObject({
    kind: "internal_note",
    body: "ข้อมูลภายใน",
    actor_id: 20,
    channel: null,
    created_at: "2026-11-03T10:00:00Z",
  });
  expect(
    normalizeWorklog(
      { ...row, is_internal: false, channel: "line_oa" },
      "legacy",
    ),
  ).toMatchObject({ kind: "public_reply", channel: "line_oa" });
});

for (const input of [
  { kind: "internal_note", body: " " },
  { kind: "public_reply", body: "reply" },
  { kind: "public_reply", body: "reply", channel: "invalid" },
  { kind: "internal_note", body: "note", channel: "email" },
  { kind: "internal_note", body: "note", actor_id: 999 },
])
  test(`reject invalid or spoofed worklog ${JSON.stringify(input)}`, () => {
    expect(() => parseWorklogInput(input)).toThrow();
  });
