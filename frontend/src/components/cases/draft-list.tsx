"use client";
import { useState } from "react";
import Link from "next/link";
import { useSession } from "@/components/providers/session-provider";
import { api } from "@/lib/api";
import type { CaseRow } from "@/lib/types";
import { Button, Input } from "@/components/ui/primitives";
function relativeTime(value: string) {
  const hours = Math.max(
    0,
    Math.floor((Date.now() - Date.parse(value)) / 3600000),
  );
  return hours >= 24
    ? `${Math.floor(hours / 24)} วันที่แล้ว`
    : hours
      ? `${hours} ชม. ที่แล้ว`
      : "ไม่ถึง 1 ชม. ที่แล้ว";
}
export function DraftList({
  rows,
  onRefresh,
}: {
  rows: CaseRow[];
  onRefresh: () => void;
}) {
  const { preview, session, href } = useSession();
  const [editing, setEditing] = useState<number | null>(null),
    [subject, setSubject] = useState(""),
    [saving, setSaving] = useState(false),
    [error, setError] = useState("");
  async function save(id: number) {
    if (preview) return;
    setSaving(true);
    setError("");
    try {
      await api(`/tickets/${id}/draft-field`, {
        method: "PATCH",
        body: JSON.stringify({ field: "subject", value: subject }),
      });
      setEditing(null);
      onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");
    } finally {
      setSaving(false);
    }
  }
  return (
    <section className="surface drafts-section">
      <div className="drafts-heading">
        <h2>
          เคสร่างของคุณ <span>{rows.length} รายการ</span>
        </h2>
        <p>
          เคสที่ยังไม่ได้ส่งและยังขาดข้อมูล
          เติมข้อมูลต่อได้ทีละช่องโดยไม่ต้องเปิดฟอร์มเต็ม
        </p>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="draft-grid">
        {rows.length ? (
          rows.map((row, index) => (
            <article className="draft-item" key={row.id}>
              <div className="draft-copy">
                <span className="draft-id">
                  {preview
                    ? `DVHT-202609-00${[425, 431, 432, 433][index]}`
                    : `ร่าง #${row.id}`}
                </span>
                <strong>{row.subject || "ยังไม่มีหัวข้อ"}</strong>
                <small>สร้างเมื่อ {relativeTime(row.created_at)}</small>
              </div>
              {session?.can_create_cases && !preview ? (
                <Button
                  size="sm"
                  onClick={() => {
                    setEditing(row.id);
                    setSubject(row.subject || "");
                  }}
                >
                  เติมข้อมูลต่อ
                </Button>
              ) : (
                <Link
                  className="button button-secondary button-sm"
                  href={href(`/cases/${row.id}`)}
                >
                  เติมข้อมูลต่อ
                </Link>
              )}
              {editing === row.id && (
                <form
                  className="draft-inline"
                  onSubmit={(e) => {
                    e.preventDefault();
                    save(row.id);
                  }}
                >
                  <label>
                    หัวข้อเคส
                    <Input
                      aria-label="หัวข้อเคส"
                      value={subject}
                      maxLength={255}
                      onChange={setSubject}
                    />
                  </label>
                  <div>
                    <Button onClick={() => setEditing(null)}>ยกเลิก</Button>
                    <Button type="submit" variant="primary" disabled={saving}>
                      {saving ? "กำลังบันทึก..." : "บันทึกช่องนี้"}
                    </Button>
                    <Link className="text-link" href={href(`/cases/${row.id}`)}>
                      ดูข้อมูลร่างทั้งหมด
                    </Link>
                  </div>
                </form>
              )}
            </article>
          ))
        ) : (
          <p className="draft-empty">ยังไม่มีเคสร่างของคุณ</p>
        )}
      </div>
    </section>
  );
}
