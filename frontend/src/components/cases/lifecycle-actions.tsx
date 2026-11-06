"use client";
import { SelectControl, TextArea } from "@/components/ui/company-fields";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { statusNames, type Ticket } from "@/lib/types";
import { Button, Input } from "@/components/ui/primitives";
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
  const [options, setOptions] = useState<Options | null>(null);
  const [target, setTarget] = useState("");
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
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
          : null;
  return (
    <section className="lifecycle-panel">
      <h3>การดำเนินการกับเคส</h3>
      <div className="lifecycle-buttons">
        {options.actions.map((action) => (
          <Button
            key={action}
            onClick={() => {
              setTarget(action);
              setValues({});
              setError("");
            }}
          >
            {action === "CANCELLED"
              ? "ยกเลิกเคส (สร้างผิด)"
              : statusNames[action] || action}
          </Button>
        ))}
      </div>
      {target && (
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
                    ? "ลูกค้านี้ยังไม่มีอินสแตนซ์ผลิตภัณฑ์ที่เปิดใช้งาน ให้ผู้ดูแลเพิ่มหรือเปิดใช้งานในทะเบียนลูกค้า แล้วรีเฟรชหน้านี้"
                    : "เคสนี้ยังไม่ได้ระบุลูกค้า จึงไม่มีอินสแตนซ์ผลิตภัณฑ์ให้เลือก"}
                </p>
              ) : needsInstance ? (
                choice(
                  "product_instance_id",
                  "อินสแตนซ์ผลิตภัณฑ์",
                  options.instances,
                )
              ) : null}
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
              เหตุผล
              <Input
                required
                maxLength={20000}
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
