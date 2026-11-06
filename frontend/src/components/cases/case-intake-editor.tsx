"use client";
import { useState, type FormEvent } from "react";
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
      <h2>หัวข้อ รายละเอียด และช่องทาง</h2>
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
            maxLength={20000}
            onValueChange={setDescription}
          />
        </label>
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
        <Button type="submit" disabled={saving}>
          {saving ? "กำลังบันทึก..." : "บันทึกการแก้ไข"}
        </Button>
        {error && <p role="alert">{error}</p>}
      </form>
    </section>
  );
}
