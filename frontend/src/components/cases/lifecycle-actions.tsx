"use client";
import { SelectControl, TextArea } from "@/components/ui/company-fields";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { statusNames, type QueuePage, type Ticket } from "@/lib/types";

const ACTION_LABELS: Record<string, string> = {
  NEW: "ส่งเป็นเคสใหม่",
  IN_PROGRESS: "เริ่มดำเนินการ",
  PENDING_CUSTOMER: "รอข้อมูลจากลูกค้า",
  PENDING_EXTERNAL: "ส่งให้ทีมพัฒนา/ภายนอก",
  RESOLVED: "บันทึกว่าแก้ไขเสร็จ",
  CLOSED: "ปิดเคส",
  REOPENED: "เปิดเคสใหม่",
  DUPLICATE: "รวมเป็นเคสซ้ำ",
  CANCELLED: "ยกเลิกเคส (สร้างผิด)",
};
const REASON_LABELS: Record<string, string> = {
  cancel_reason: "เหตุผลที่ยกเลิก",
  reopen_reason: "ลูกค้าแจ้งว่ายังพบปัญหาอะไร",
  pending_external_reason: "กำลังรออะไรจากทีมพัฒนา/ภายนอก",
  pending_customer_reason: "กำลังรออะไรจากลูกค้า",
  sla_breach_reason: "เคสนี้เกิน SLA — เหตุผลที่เกิน (ใช้วิเคราะห์เชิงระบบ ไม่ใช่การลงโทษ)",
};
import { Button, Input } from "@/components/ui/primitives";
import { useSession } from "@/components/providers/session-provider";
import { CustomerSystemEditor } from "./customer-system-editor";
type Choice = { id: number; name: string };
type Options = {
  actions: string[];
  assignees: Choice[];
  causes: Choice[];
  solutions: Choice[];
  instances: (Choice & { product_id: number })[];
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
  const [catalog, setCatalog] = useState<{
    product_id: number;
    modules: Choice[];
    problem_types: (Choice & { module_id: number })[];
  }>();
  const instance = options?.instances.find((row) => row.id === Number(values.product_instance_id));
  const productId = target === "RESOLVED" ? instance?.product_id : undefined;
  useEffect(() => {
    if (!productId) return;
    const controller = new AbortController();
    api<NonNullable<typeof catalog>>(`/products/${productId}/case-options`, { signal: controller.signal })
      .then(setCatalog)
      .catch(() => {
        if (!controller.signal.aborted) setError("โหลดโมดูลและประเภทปัญหาไม่สำเร็จ");
      });
    return () => controller.abort();
  }, [productId]);
  if (!options?.actions.length) return null;
  const activeCatalog = productId && catalog?.product_id === productId ? catalog : undefined;
  const modules = activeCatalog?.modules ?? [];
  const categories = activeCatalog?.problem_types.filter(
    (row) => row.module_id === Number(values.module_id),
  ) ?? [];
  const canResolve = Boolean(instance && modules.some((row) => row.id === Number(values.module_id)) &&
    categories.some((row) => row.id === Number(values.category_id)));
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
            setValues((current) => ({ ...current, [field]: nextValue,
              ...(field === "product_instance_id" ? { module_id: "", category_id: "" } : {}),
              ...(field === "module_id" ? { category_id: "" } : {}),
            }))
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
      if (value && key !== "master_ticket_no")
        body[key] = key.endsWith("_id") ? Number(value) : value;
    });
    try {
      if (target === "DUPLICATE") {
        const number = (values.master_ticket_no || "").trim().toUpperCase();
        const found = await api<QueuePage>(
          `/case-queue?scope=all&limit=5&q=${encodeURIComponent(number)}`,
        );
        const master = found.items.find((row) => row.ticket_no === number);
        if (!master) throw new Error(`ไม่พบเคสเลข ${number} กรุณาตรวจเลขเคสหลักอีกครั้ง`);
        body.master_ticket_id = master.id;
      }
      const updated = await api<Ticket>(`/tickets/${ticket.id}/status`, {
          method: "PATCH",
          body: JSON.stringify(body),
        });
      onUpdated(updated);
      setTarget("");
      setValues({});
      setMessage(target === "DUPLICATE" && updated.status !== "DUPLICATE"
        ? "รวมข้อมูลแล้ว เคสนี้จะเปลี่ยนเป็นเคสซ้ำเมื่อปิดเคสหลัก"
        : "เปลี่ยนสถานะแล้ว");
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
      <h3>อัปเดตสถานะเคส</h3>
      <div className="lifecycle-buttons">
        {options.actions.filter((action) => !(action === "IN_PROGRESS" && ticket.status === "NEW" && !ticket.assignee_id)).map((action) => (
          <Button
            key={action}
            disabled={busy || editingSystems}
            onClick={() => {
              setTarget(action);
              setValues(action === "RESOLVED" ? {
                product_instance_id: options.instances.some((row) => row.id === ticket.product_instance_id)
                  ? String(ticket.product_instance_id) : "",
                module_id: ticket.module_id ? String(ticket.module_id) : "",
                category_id: ticket.category_id ? String(ticket.category_id) : "",
                root_cause_code_id: options.causes.some((cause) => cause.id === ticket.root_cause_code_id)
                  ? String(ticket.root_cause_code_id) : "",
                resolution_code_id: options.solutions.some((solution) => solution.id === ticket.resolution_code_id)
                  ? String(ticket.resolution_code_id) : "",
                resolution_detail: ticket.resolution_detail ?? "",
              } : {});
              setError("");
              setMessage("");
            }}
          >
            {ACTION_LABELS[action] || statusNames[action] || action}
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
                    {
                      id: system.id,
                      name: system.name,
                      product_id: system.product_id,
                    },
                  ],
                },
            );
            setValues((current) => ({
              ...current,
              product_instance_id: String(system.id),
              module_id: "",
              category_id: "",
            }));
            setMessage(`เลือกใช้ระบบ ${system.name} แล้ว`);
            setEditingSystems(false);
          }}
        />
      )}
      {target && !editingSystems && (
        <form onSubmit={submit} className="lifecycle-form">
          <strong>
            {ACTION_LABELS[target] || statusNames[target] || target}
          </strong>
          {target === "IN_PROGRESS" &&
            !ticket.assignee_id &&
            choice("assignee_id", "ผู้ดำเนินการ", options.assignees)}
          {target === "RESOLVED" && (
            <>
              {missingInstance ? (
                <p role="alert" className="form-error">
                  {ticket.organization_id
                    ? canManageSystems
                      ? "ลูกค้านี้ยังไม่มีระบบที่เปิดใช้งาน เพิ่มหรือเปิดใช้งานระบบได้ด้านล่าง"
                      : "ลูกค้านี้ยังไม่มีระบบที่เปิดใช้งาน ให้ผู้ที่มีสิทธิ์แก้ข้อมูลลูกค้าเปิดหน้านี้เพื่อเพิ่มระบบ"
                    : "เคสนี้ยังไม่ได้ระบุลูกค้า จึงไม่มีระบบให้เลือก"}
                </p>
              ) : (
                choice(
                  "product_instance_id",
                  "ระบบที่ลูกค้าใช้งาน",
                  options.instances,
                )
              )}
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
              {activeCatalog && choice("module_id", "โมดูล", modules)}
              {values.module_id && activeCatalog && choice("category_id", "ประเภทปัญหา", categories)}
              {activeCatalog && (!modules.length || (values.module_id && !categories.length)) && (
                <p>ตรวจว่าระบบนี้มีโมดูลและประเภทปัญหาที่เปิดใช้งานใน Master Data</p>
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
              {REASON_LABELS[reason]}
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
              เลขเคสหลักที่จะรวมเข้าไป
              <Input
                required
                placeholder="เช่น DVHT-202611-00001"
                value={values.master_ticket_no || ""}
                onChange={(value) =>
                  setValues({ ...values, master_ticket_no: value })
                }
              />
            </label>
          )}
          <div className="lifecycle-buttons">
            <Button onClick={() => setTarget("")}>ยกเลิก</Button>
            <Button
              type="submit"
              variant="primary"
              disabled={busy || (target === "RESOLVED" && !canResolve)}
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
