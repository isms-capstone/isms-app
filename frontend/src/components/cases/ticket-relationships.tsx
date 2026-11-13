"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button, Input } from "@/components/ui/primitives";

const labels = {
  duplicate: "เคสซ้ำ",
  related: "เกี่ยวข้องกัน",
  "follow-up": "ติดตามผล",
  "caused-by": "เกิดจาก",
  "child-of": "เคสย่อยของเหตุการณ์หลัก",
};

type CaseLink = {
  id: number;
  ticket_id: number;
  related_ticket_id: number;
  relationship_type: keyof typeof labels;
};

export function TicketRelationships({
  id,
  editable,
  revision,
  onUpdated,
}: {
  id: number;
  editable: boolean;
  revision: string;
  onUpdated: () => void;
}) {
  const [rows, setRows] = useState<CaseLink[]>();
  const [kind, setKind] = useState<keyof typeof labels>("related");
  const [target, setTarget] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    api<CaseLink[]>(`/tickets/${id}/links`, { signal: controller.signal })
      .then(setRows)
      .catch((error) => {
        if (!controller.signal.aborted) setError(error.message);
      });
    return () => controller.abort();
  }, [id, revision]);

  async function save() {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const merging = kind === "duplicate";
      const result = await api<{ status?: string }>(
        `/tickets/${id}/${merging ? "merge-duplicate" : "links"}`,
        {
          method: "POST",
          body: JSON.stringify(
            merging
              ? { master_ticket_id: Number(target), reason }
              : {
                  related_ticket_id: Number(target),
                  relationship_type: kind,
                  reason,
                },
          ),
        },
      );
      setMessage(
        merging && result.status !== "DUPLICATE"
          ? "รวมข้อมูลแล้ว เคสนี้จะเปลี่ยนเป็นเคสซ้ำเมื่อปิดเคสหลัก"
          : "บันทึกความสัมพันธ์แล้ว",
      );
      setTarget("");
      setReason("");
      onUpdated();
    } catch (error) {
      setError(error instanceof Error ? error.message : "บันทึกไม่สำเร็จ");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="surface detail-card ticket-relationships">
      <h2>เคสที่เชื่อมโยง</h2>
      {rows?.length ? (
        <ul className="mb-4 space-y-2">
          {rows.map((row) => {
            const outgoing = row.ticket_id === id;
            const other = outgoing ? row.related_ticket_id : row.ticket_id;
            return (
              <li key={row.id}>
                {labels[row.relationship_type]}{" "}
                {row.relationship_type !== "related" &&
                  (outgoing ? "ไปยัง" : "จาก")}{" "}
                <Link className="text-link" href={`/cases/${other}`}>
                  เคส #{other}
                </Link>
              </li>
            );
          })}
        </ul>
      ) : (
        rows && <p className="mb-4">ยังไม่มีเคสที่เชื่อมโยง</p>
      )}
      {editable && (
        <form
          className="space-y-3"
          onSubmit={(event) => {
            event.preventDefault();
            void save();
          }}
        >
          <div className="detail-grid">
            <label>
              ประเภทความสัมพันธ์
              <select
                className="input block w-full"
                value={kind}
                onChange={(e) => setKind(e.target.value as keyof typeof labels)}
              >
                {Object.entries(labels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              ID ของเคสปลายทาง
              <Input
                type="number"
                required
                min={1}
                value={target}
                onChange={(value) => setTarget(value)}
              />
            </label>
            <label>
              เหตุผล
              <Input
                required
                maxLength={500}
                value={reason}
                onChange={(value) => setReason(value)}
              />
            </label>
          </div>
          {kind === "duplicate" && (
            <p>ข้อความและไฟล์แนบจะย้ายไปเคสหลักขององค์กรเดียวกัน</p>
          )}
          <Button variant="primary" type="submit" disabled={saving || !target || !reason.trim()}>
            {kind === "duplicate" ? "รวมเข้าเคสหลัก" : "เชื่อมเคส"}
          </Button>
        </form>
      )}
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
