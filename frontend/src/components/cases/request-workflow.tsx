"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Ticket } from "@/lib/types";
import { Button, Input } from "@/components/ui/primitives";
import { useSession } from "@/components/providers/session-provider";
import { backendCapabilities } from "@/lib/backend-capabilities";

export function RequestWorkflow({
  ticket,
  onUpdated,
}: {
  ticket: Ticket;
  onUpdated: (ticket: Ticket) => void;
}) {
  const { session } = useSession();
  const [workflow, setWorkflow] = useState("");
  const [assignees, setAssignees] = useState<{ id: number; name: string }[]>(
    [],
  );
  const [assignee, setAssignee] = useState("");
  const [detail, setDetail] = useState("");
  const [breachReason, setBreachReason] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    backendCapabilities(controller.signal)
      .then(async (capabilities) => {
        if (!capabilities.categorization || !capabilities.requestWorkflow)
          return;
        const [classification, options] = await Promise.all([
          api<{ workflow: string }>(`/tickets/${ticket.id}/categorization`, {
            signal: controller.signal,
          }),
          api<{ assignees: { id: number; name: string }[] }>(
            `/tickets/${ticket.id}/lifecycle-options`,
            { signal: controller.signal },
          ),
        ]);
        setWorkflow(classification.workflow);
        setAssignees(options.assignees);
      })
      .catch(() => {});
    return () => controller.abort();
  }, [ticket]);
  if (workflow !== "request") return null;
  const participant =
    session?.role === "Admin" ||
    [ticket.created_by_id, ticket.owner_id, ticket.assignee_id].includes(
      session?.id ?? -1,
    );
  const action = !participant
    ? null
    : ["NEW", "REOPENED"].includes(ticket.status)
      ? "start"
      : ticket.status === "IN_PROGRESS"
        ? "fulfil"
        : ticket.status === "RESOLVED" && session?.role === "Admin"
          ? "confirm"
          : null;
  return (
    <section className="surface detail-card request-workflow">
      <h2>คำขอบริการ (Request)</h2>
      <p>รับคำขอ → ดำเนินคำขอ → ส่งมอบผล → ยืนยันและปิดคำขอ</p>
      {action && (
        <form
          className="worklog-composer"
          onSubmit={async (event) => {
            event.preventDefault();
            if (busy) return;
            setBusy(true);
            setError("");
            try {
              onUpdated(
                await api<Ticket>(`/tickets/${ticket.id}/request-workflow`, {
                  method: "POST",
                  body: JSON.stringify({
                    action,
                    assignee_id: assignee ? Number(assignee) : null,
                    fulfilment_detail: detail || null,
                    ...(action === "confirm" && breachReason
                      ? { sla_breach_reason: breachReason }
                      : {}),
                  }),
                }),
              );
            } catch (e) {
              setError(e instanceof Error ? e.message : "ดำเนินการไม่สำเร็จ");
            } finally {
              setBusy(false);
            }
          }}
        >
          {action === "start" && (
            <label>
              ผู้ดำเนินคำขอ
              <select
                aria-label="ผู้ดำเนินคำขอ"
                required={!ticket.assignee_id}
                value={assignee}
                onChange={(event) => setAssignee(event.target.value)}
              >
                <option value="">
                  {ticket.assignee_id
                    ? "ใช้ผู้รับผิดชอบปัจจุบัน"
                    : "เลือกผู้ดำเนินคำขอ"}
                </option>
                {assignees.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          {action === "fulfil" && (
            <>
              <p className="field-hint">
                ระบุหมวดหมู่ รหัสสาเหตุ และรหัสวิธีแก้ให้ครบก่อนส่งมอบ
              </p>
              <label>
                ผลการส่งมอบคำขอ
                <textarea
                  aria-label="ผลการส่งมอบคำขอ"
                  required
                  maxLength={20000}
                  value={detail}
                  onChange={(event) => setDetail(event.target.value)}
                />
              </label>
            </>
          )}
          {action === "confirm" && ticket.sla_breached && (
            <label>
              เหตุผลที่เกิน SLA
              <Input
                required
                maxLength={2000}
                value={breachReason}
                onChange={setBreachReason}
              />
            </label>
          )}
          <Button type="submit" disabled={busy}>
            {action === "start"
              ? "เริ่มดำเนินคำขอ"
              : action === "fulfil"
                ? "ส่งมอบผลคำขอ"
                : "ยืนยันและปิดคำขอ"}
          </Button>
        </form>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
