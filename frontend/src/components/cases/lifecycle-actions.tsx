"use client";
import { SelectControl, TextArea } from "@/components/ui/company-fields";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { statusNames, type Ticket } from "@/lib/types";
import { Button, Input } from "@/components/ui/primitives";
import { useSession } from "@/components/providers/session-provider";
import { CustomerSystemEditor } from "./customer-system-editor";
type Choice = { id: number; name: string };
type Options = {
  actions: string[];
  assignees: Choice[];
  causes: Choice[];
  solutions: Choice[];
  categories: Choice[];
  instances: Choice[];
};

export function LifecycleActions({
  ticket,
  onUpdated,
}: {
  ticket: Ticket;
  onUpdated: (ticket: Ticket) => void;
}) {
  const { session } = useSession();
  const [options, setOptions] = useState<Options | null>(null);
  const [target, setTarget] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [editingSystems, setEditingSystems] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    api<Options>(`/tickets/${ticket.id}/lifecycle-options`, {
      signal: controller.signal,
    })
      .then(setOptions)
      .catch(() => setOptions(null));
    return () => controller.abort();
  }, [ticket.id, ticket.status]);
  if (!options?.actions.length) return null;
  const needsInstance =
    target === "RESOLVED" &&
    !options.instances.some(
      (instance) => instance.id === ticket.product_instance_id,
    );
  const missingInstance = needsInstance && options.instances.length === 0;
  const canManageSystems = Boolean(
    ticket.organization_id && session?.can_edit_customers,
  );
  function choice(field: string, label: string, rows: Choice[]) {
    return (
      <label key={field}>
        {label}
        <SelectControl
          required
          value={values[field] || ""}
          onValueChange={(nextValue) =>
            setValues({ ...values, [field]: nextValue })
          }
        >
          <option value="">เลือก{label}</option>
          {rows.map((row) => (
            <option key={row.id} value={row.id}>
              {row.name}
            </option>
          ))}
        </SelectControl>
      </label>
    );
  }
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    const body: Record<string, string | number> = { status: target };
    Object.entries(values).forEach(([key, value]) => {
      if (value) body[key] = key.endsWith("_id") ? Number(value) : value;
    });
    try {
      onUpdated(
        await api<Ticket>(`/tickets/${ticket.id}/status`, {
          method: "PATCH",
          body: JSON.stringify(body),
        }),
      );
      setTarget("");
      setValues({});
      setMessage("เปลี่ยนสถานะแล้ว");
    } catch (e) {
      setError(e instanceof Error ? e.message : "เปลี่ยนสถานะไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }
  const reason =
    target === "CANCELLED"
      ? "cancel_reason"
      : target === "REOPENED"
        ? "reopen_reason"
        : target === "PENDING_EXTERNAL"
          ? "pending_external_reason"
          : target === "PENDING_CUSTOMER"
            ? "pending_customer_reason"
            : target === "CLOSED" && ticket.sla_breached
              ? "sla_breach_reason"
              : null;
  return (
    <section className="lifecycle-panel">
      <h3>การดำเนินการกับเคส</h3>
      <div className="lifecycle-buttons">
        {options.actions.map((action) => (
          <Button
            key={action}
            disabled={busy || editingSystems}
            onClick={() => {
              setTarget(action);
              setValues(
                action === "RESOLVED"
                  ? {
                      root_cause_code_id: options.causes.some(
                        (cause) => cause.id === ticket.root_cause_code_id,
                      )
                        ? String(ticket.root_cause_code_id)
                        : "",
                      resolution_code_id: options.solutions.some(
                        (solution) => solution.id === ticket.resolution_code_id,
                      )
                        ? String(ticket.resolution_code_id)
                        : "",
                      resolution_detail: ticket.resolution_detail ?? "",
                    }
                  : {},
              );
              setError("");
              setMessage("");
            }}
          >
            {action === "CANCELLED"
              ? "ยกเลิกเคส (สร้างผิด)"
              : statusNames[action] || action}
          </Button>
        ))}
      </div>
      {editingSystems && ticket.organization_id && (
        <CustomerSystemEditor
          key={ticket.organization_id}
          organizationId={ticket.organization_id}
          onCancel={() => setEditingSystems(false)}
          onSaved={(system) => {
            setOptions(
              (current) =>
                current && {
                  ...current,
                  instances: [
                    ...current.instances.filter(
                      (item) => item.id !== system.id,
                    ),
                    { id: system.id, name: system.name },
                  ],
                },
            );
            setValues((current) => ({
              ...current,
              product_instance_id: String(system.id),
            }));
            setMessage(`เลือกใช้ระบบ ${system.name} แล้ว`);
            setEditingSystems(false);
          }}
        />
      )}
      {target && !editingSystems && (
        <form onSubmit={submit} className="lifecycle-form">
          <strong>
            {target === "CANCELLED"
              ? "ยกเลิกเคส (สร้างผิด)"
              : statusNames[target] || target}
          </strong>
          {target === "IN_PROGRESS" &&
            !ticket.assignee_id &&
            choice("assignee_id", "ผู้ดำเนินการ", options.assignees)}
          {target === "RESOLVED" && (
            <>
              {!ticket.category_id &&
                choice("category_id", "ประเภทปัญหา", options.categories)}
              {missingInstance ? (
                <p role="alert" className="form-error">
                  {ticket.organization_id
                    ? canManageSystems
                      ? "ลูกค้านี้ยังไม่มีระบบที่เปิดใช้งาน เพิ่มหรือเปิดใช้งานระบบได้ด้านล่าง"
                      : "ลูกค้านี้ยังไม่มีระบบที่เปิดใช้งาน ให้ผู้ที่มีสิทธิ์แก้ข้อมูลลูกค้าเปิดหน้านี้เพื่อเพิ่มระบบ"
                    : "เคสนี้ยังไม่ได้ระบุลูกค้า จึงไม่มีระบบให้เลือก"}
                </p>
              ) : needsInstance ? (
                choice(
                  "product_instance_id",
                  "ระบบที่ลูกค้าใช้งาน",
                  options.instances,
                )
              ) : null}
              {needsInstance && canManageSystems && (
                <div>
                  <Button
                    onClick={() => setEditingSystems(true)}
                    disabled={busy}
                  >
                    เพิ่มหรือเปิดใช้งานระบบของลูกค้า
                  </Button>
                </div>
              )}
              {choice("root_cause_code_id", "สาเหตุปัญหา", options.causes)}
              {choice("resolution_code_id", "วิธีแก้ไข", options.solutions)}
              <label>
                รายละเอียดการแก้ไข
                <TextArea
                  required
                  maxLength={20000}
                  value={values.resolution_detail || ""}
                  onValueChange={(nextValue) =>
                    setValues({ ...values, resolution_detail: nextValue })
                  }
                />
              </label>
            </>
          )}
          {reason && (
            <label>
              {reason === "pending_customer_reason"
                ? "ข้อมูลที่รอจากลูกค้า"
                : reason === "sla_breach_reason"
                  ? "เหตุผลที่เกิน SLA"
                  : "เหตุผล"}
              <Input
                required
                maxLength={
                  reason === "pending_customer_reason" ||
                  reason === "sla_breach_reason"
                    ? 2000
                    : 20000
                }
                aria-label="เหตุผลเปลี่ยนสถานะ"
                value={values[reason] || ""}
                onChange={(value) => setValues({ ...values, [reason]: value })}
              />
            </label>
          )}
          {target === "DUPLICATE" && (
            <label>
              เลข ID เคสหลัก
              <Input
                required
                type="number"
                min={1}
                value={values.master_ticket_id || ""}
                onChange={(value) =>
                  setValues({ ...values, master_ticket_id: value })
                }
              />
            </label>
          )}
          <div className="lifecycle-buttons">
            <Button onClick={() => setTarget("")}>ยกเลิก</Button>
            <Button
              type="submit"
              variant="primary"
              disabled={busy || missingInstance}
            >
              ยืนยันเปลี่ยนสถานะ
            </Button>
          </div>
        </form>
      )}
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
    </section>
  );
}
