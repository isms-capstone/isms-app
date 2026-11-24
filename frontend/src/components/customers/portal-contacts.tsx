"use client";
import { useEffect, useState } from "react";
import { useSession } from "@/components/providers/session-provider";
import { api } from "@/lib/api";

type Contact = {
  id: number;
  name: string;
  is_active: boolean;
  portal_scope: "own" | "organization";
  channels: { channel_type: string; value: string }[];
};

/** POR-08: who may see which cases in the customer portal. */
export function PortalContacts({ organizationId }: { organizationId: number }) {
  const { session } = useSession();
  const [contacts, setContacts] = useState<Contact[]>([]),
    [error, setError] = useState(""),
    [saving, setSaving] = useState<number | null>(null);
  useEffect(() => {
    if (!session) return;
    const controller = new AbortController();
    api<Contact[]>(`/customers/contacts?organization_id=${organizationId}&limit=100`, {
      signal: controller.signal,
    })
      .then(setContacts)
      .catch((e) => !controller.signal.aborted && setError(e.message));
    return () => controller.abort();
  }, [organizationId, session]);

  async function setScope(contact: Contact, organization: boolean) {
    setSaving(contact.id);
    setError("");
    try {
      const result = await api<{ scope: Contact["portal_scope"] }>(`/portal/contacts/${contact.id}/scope`, {
        method: "PUT",
        body: JSON.stringify({ scope: organization ? "organization" : "own" }),
      });
      setContacts((rows) => rows.map((row) => (row.id === contact.id ? { ...row, portal_scope: result.scope } : row)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");
    } finally {
      setSaving(null);
    }
  }

  const editable = !!session?.can_edit_customers;
  return (
    <section className="surface detail-card">
      <h2>ผู้ติดต่อในศูนย์ช่วยเหลือลูกค้า</h2>
      <p className="field-hint">
        ผู้ติดต่อเข้าดูเคสได้ด้วยอีเมลที่ลงทะเบียนไว้ โดยปกติเห็นเฉพาะเคสที่ตัวเองแจ้ง
        ถ้าเป็นผู้ประสานงานขององค์กร ให้เปิดสิทธิ์ดูทุกเคสขององค์กร
      </p>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {contacts.length === 0 ? (
        <p className="text-muted">ยังไม่มีผู้ติดต่อ</p>
      ) : (
        <table className="case-table">
          <thead>
            <tr>
              <th>ผู้ติดต่อ</th>
              <th>อีเมลสำหรับเข้าสู่ระบบ</th>
              <th>เห็นทุกเคสขององค์กร</th>
            </tr>
          </thead>
          <tbody>
            {contacts.map((contact) => {
              const emails = contact.channels.filter((c) => c.channel_type === "email").map((c) => c.value);
              return (
                <tr key={contact.id}>
                  <td>
                    {contact.name}
                    {!contact.is_active && <small className="text-muted"> (ปิดใช้งาน)</small>}
                  </td>
                  <td>{emails.join(", ") || <span className="text-muted">ยังไม่มีอีเมล — เข้าศูนย์ช่วยเหลือไม่ได้</span>}</td>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`${contact.name} เห็นทุกเคสขององค์กร`}
                      checked={contact.portal_scope === "organization"}
                      disabled={!editable || saving === contact.id}
                      onChange={(event) => setScope(contact, event.target.checked)}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </section>
  );
}
