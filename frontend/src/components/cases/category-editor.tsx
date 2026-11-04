"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Ticket, Instance, SelectionContext } from "@/lib/types";
import { useSession } from "@/components/providers/session-provider";
import { Button } from "@/components/ui/primitives";
import {
  CategoryFields,
  CategorySelect,
  type CategoryValues,
} from "./category-fields";
import { backendCapabilities } from "@/lib/backend-capabilities";

type CategoryState = CategoryValues & {
  product_id: number | null;
  product_instance_id: number | null;
  workflow: string;
};
export function CategoryEditor({
  ticket,
  onUpdated,
}: {
  ticket: Ticket;
  onUpdated: (ticket: Ticket) => void;
}) {
  const { session } = useSession();
  const [value, setValue] = useState<CategoryState | null>(null);
  const [original, setOriginal] = useState<CategoryState | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);
  const [supported, setSupported] = useState<boolean | null>(null);
  const [instances, setInstances] = useState<Instance[]>([]);
  const dirty = useRef(false);
  useEffect(() => {
    const controller = new AbortController();
    backendCapabilities(controller.signal)
      .then(async (capabilities) => {
        setSupported(capabilities.categorization);
        if (!capabilities.categorization) return;
        const result = await api<CategoryState>(
          `/tickets/${ticket.id}/categorization`,
          { signal: controller.signal },
        );
        if (!dirty.current) {
          setValue(result);
          setOriginal(result);
        }
        if (ticket.organization_id) {
          const context = await api<SelectionContext>(
            `/customers/organizations/${ticket.organization_id}/selection-context`,
            { signal: controller.signal },
          );
          setInstances(context.instances);
        }
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [ticket, retry]);
  const editable =
    session?.can_create_cases &&
    (session.role === "Admin" ||
      [ticket.created_by_id, ticket.owner_id, ticket.assignee_id].includes(
        session.id,
      ));
  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!value || busy || loading) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      // The read response may include display metadata; send only editable fields.
      const body = Object.fromEntries(
        Object.entries(value).filter(
          ([key, next]) =>
            !["product_id", "workflow", "suggested_severity"].includes(key) &&
            JSON.stringify(next) !==
              JSON.stringify(original?.[key as keyof CategoryState]),
        ),
      );
      // An explicit override may equal the old severity while its assessment inputs changed.
      if (
        "impact_scope" in body ||
        "is_exam_window" in body ||
        "severity_overridden_reason" in body
      ) {
        body.severity = value.severity;
      }
      const updated = await api<Ticket>(
        `/tickets/${ticket.id}/categorization`,
        { method: "PATCH", body: JSON.stringify(body) },
      );
      const refreshed = await api<CategoryState>(
        `/tickets/${ticket.id}/categorization`,
      );
      setValue(refreshed);
      setOriginal(refreshed);
      dirty.current = false;
      onUpdated(updated);
      setMessage("บันทึกหมวดหมู่และประวัติการเปลี่ยนแล้ว");
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="surface detail-card category-editor">
      <h2>หมวดหมู่และการประเมินเคส</h2>
      {supported === false && (
        <p className="field-hint">
          ยังไม่สามารถแก้หมวดหมู่เพิ่มเติมได้ในระบบที่เชื่อมต่ออยู่
        </p>
      )}
      {value && (
        <form onSubmit={save}>
          <fieldset disabled={!editable || busy}>
            <CategorySelect
              label="ผลิตภัณฑ์ / ระบบที่ลูกค้าใช้งาน"
              value={value.product_instance_id}
              options={instances.map((instance) => ({
                id: instance.id,
                name: `${instance.name} · ${instance.version} · ${instance.environment}`,
              }))}
              disabled={!editable || busy || !ticket.organization_id}
              onChange={(next) => {
                dirty.current = true;
                const selected = instances.find(
                  (instance) => instance.id === Number(next),
                );
                setValue({
                  ...value,
                  product_instance_id: selected?.id ?? null,
                  product_id: selected?.product_id ?? null,
                  module_id: null,
                  category_id: null,
                  symptom_id: null,
                  service_stage_id: null,
                });
              }}
            />
            <CategoryFields
              key={ticket.id}
              productId={value.product_id}
              organizationId={ticket.organization_id}
              departmentId={ticket.department_id}
              value={value}
              readOnly={!editable || busy}
              onChange={(next) => {
                dirty.current = true;
                setValue({ ...value, ...next });
              }}
              onLoading={setLoading}
            />
          </fieldset>
          {editable && (
            <Button type="submit" variant="primary" disabled={busy || loading}>
              {busy ? "กำลังบันทึก…" : "บันทึกหมวดหมู่"}
            </Button>
          )}
        </form>
      )}
      {error && (
        <p role="alert" className="form-error">
          {error}{" "}
          <button type="button" onClick={() => setRetry((n) => n + 1)}>
            ลองอีกครั้ง
          </button>
        </p>
      )}
      {message && (
        <p role="status" className="form-message">
          {message}
        </p>
      )}
    </section>
  );
}
