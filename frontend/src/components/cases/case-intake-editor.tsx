"use client";
import { useEffect, useState, type FormEvent } from "react";
import { api } from "@/lib/api";
import { channelNames, type Ticket } from "@/lib/types";
import { Button, Input } from "@/components/ui/primitives";
import { SelectControl, TextArea } from "@/components/ui/company-fields";

export function CaseIntakeEditor({
  ticket,
  onUpdated,
}: {
  ticket: Ticket;
  onUpdated: (ticket: Ticket) => void;
}) {
  const [subject, setSubject] = useState(ticket.subject || "");
  const [description, setDescription] = useState(ticket.description || "");
  const [channel, setChannel] = useState(ticket.channel || "");
  const [contact, setContact] = useState(
    ticket.contact_id ? String(ticket.contact_id) : "",
  );
  const [contacts, setContacts] = useState<{ id: number; name: string }[]>([]);
  useEffect(() => {
    if (!ticket.organization_id) return;
    const controller = new AbortController();
    api<{ id: number; name: string; is_active?: boolean }[]>(
      `/customers/contacts?organization_id=${ticket.organization_id}&limit=100`,
      { signal: controller.signal },
    )
      .then((rows) => setContacts(rows.filter((row) => row.is_active !== false)))
      .catch(() => {});
    return () => controller.abort();
  }, [ticket.organization_id]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  async function save(event: FormEvent) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setError("");
    try {
      onUpdated(
        await api<Ticket>(`/tickets/${ticket.id}/details`, {
          method: "PATCH",
          body: JSON.stringify({
            subject,
            description: description || null,
            channel,
            contact_id: contact ? Number(contact) : null,
          }),
        }),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");
    } finally {
      setSaving(false);
    }
  }
  return (
    <section className="mt-4">
      <h2>หัวข้อ รายละเอียด ผู้แจ้ง และช่องทาง</h2>
      <form className="detail-edit" onSubmit={save}>
        <label>
          หัวข้อเคส
          <Input
            value={subject}
            required
            maxLength={255}
            onChange={setSubject}
          />
        </label>
        <label>
          รายละเอียด
          <TextArea
            value={description}
            placeholder="อาการที่พบ ขั้นตอนที่ทำ และผลที่ลูกค้าเห็น"
            maxLength={20000}
            onValueChange={setDescription}
          />
        </label>
        {contacts.length > 0 && (
          <label>
            ผู้แจ้ง
            <SelectControl value={contact} onValueChange={setContact}>
              <option value="">ไม่ระบุผู้แจ้ง</option>
              {contacts.map((row) => (
                <option key={row.id} value={String(row.id)}>
                  {row.name}
                </option>
              ))}
            </SelectControl>
          </label>
        )}
        <label>
          ช่องทาง
          <SelectControl value={channel} required onValueChange={setChannel}>
            <option value="">เลือกช่องทาง</option>
            {Object.entries(channelNames).map(([id, label]) => (
              <option key={id} value={id}>
                {label}
              </option>
            ))}
          </SelectControl>
        </label>
        <Button variant="primary" type="submit" disabled={saving}>
          {saving ? "กำลังบันทึก..." : "บันทึกการแก้ไข"}
        </Button>
        {error && <p role="alert">{error}</p>}
      </form>
    </section>
  );
}
