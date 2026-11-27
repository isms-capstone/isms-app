"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { formatDateTime, formatShortDate } from "@/lib/format";
import { api } from "@/lib/api";
import { Button, Input } from "@/components/ui/primitives";
import { SelectControl } from "@/components/ui/company-fields";

type Problem = {
  product_name: string | null;
  module_name: string | null;
  category_name: string | null;
  symptom_name: string | null;
  frequency: number;
  last_reported_at: string;
};
type Contract = { contract_start_date: string | null; contract_end_date: string | null };
type ExamWindow = { id: number; name: string; starts_at: string; ends_at: string; is_active: boolean };
type Named = { id: number; name: string; is_active: boolean; kind?: "course" | "exam" };

const CHANNELS = [
  ["email", "อีเมล"],
  ["phone", "โทรศัพท์"],
  ["line_user_id", "LINE userId"],
] as const;

/**
 * CUS-03/04/05: everything staff need about one customer in the main web app —
 * open cases and frequent problems, contract and exam calendar, departments,
 * courses/exams and contacts.
 */
export function CustomerProfile({
  organizationId,
  canEdit,
  onContactsChanged,
}: {
  organizationId: number;
  canEdit: boolean;
  onContactsChanged: () => void;
}) {
  const base = `/customers/organizations/${organizationId}`;
  const [openCount, setOpenCount] = useState<number | null>(null);
  const [problems, setProblems] = useState<Problem[]>([]);
  const [contract, setContract] = useState<Contract>({ contract_start_date: null, contract_end_date: null });
  const [windows, setWindows] = useState<ExamWindow[]>([]);
  const [departments, setDepartments] = useState<Named[]>([]);
  const [courses, setCourses] = useState<Named[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const get = <T,>(path: string) => api<T>(`${base}${path}`, { signal: controller.signal });
    Promise.all([
      get<{ open_count: number }>("/case-summary"),
      get<Problem[]>("/problem-history?limit=10"),
      get<Contract>("/contract"),
      get<ExamWindow[]>("/exam-windows"),
      get<Named[]>("/departments"),
      get<Named[]>("/courses"),
    ])
      .then(([summary, history, terms, exams, depts, items]) => {
        setOpenCount(summary.open_count);
        setProblems(history);
        setContract(terms);
        setWindows(exams);
        setDepartments(depts);
        setCourses(items);
      })
      .catch((e) => !controller.signal.aborted && setError(e.message));
    return () => controller.abort();
  }, [base, reload]);

  const save = useCallback(
    async (path: string, method: string, body: unknown, done: string) => {
      setError("");
      setMessage("");
      try {
        await api(`${base}${path}`, { method, body: JSON.stringify(body) });
        setMessage(done);
        setReload((n) => n + 1);
        return true;
      } catch (e) {
        setError(e instanceof Error ? e.message : "บันทึกไม่สำเร็จ");
        return false;
      }
    },
    [base],
  );

  return (
    <section className="surface detail-card customer-profile" aria-label="ข้อมูลลูกค้า">
      <div className="customer-profile-summary">
        <div>
          <span className="field-hint">เคสที่เปิดอยู่</span>
          <strong>{openCount ?? "—"}</strong>
        </div>
        <div>
          <span className="field-hint">สัญญา</span>
          <strong>
            {contract.contract_start_date ? formatShortDate(contract.contract_start_date) : "ยังไม่ระบุ"} →{" "}
            {contract.contract_end_date ? formatShortDate(contract.contract_end_date) : "ยังไม่ระบุ"}
          </strong>
        </div>
        <div>
          <span className="field-hint">ช่วงสอบที่กำลังจะถึง</span>
          <strong>
            {windows.filter((row) => row.is_active && new Date(row.ends_at) > new Date()).length} ช่วง
          </strong>
        </div>
      </div>

      <h2>ปัญหาที่พบบ่อย</h2>
      {problems.length === 0 ? (
        <p className="field-hint">ยังไม่มีประวัติปัญหา (นับเคสใหม่และเคสที่แก้แล้ว ไม่รวมร่าง เคสซ้ำ และเคสยกเลิก)</p>
      ) : (
        <table className="customer-list">
          <thead>
            <tr>
              <th>ผลิตภัณฑ์ / โมดูล</th>
              <th>ประเภทปัญหา / อาการ</th>
              <th>จำนวนครั้ง</th>
              <th>แจ้งล่าสุด</th>
            </tr>
          </thead>
          <tbody>
            {problems.map((row, index) => (
              <tr key={index}>
                <td>{row.product_name || "ยังไม่ระบุ"} · {row.module_name || "—"}</td>
                <td>{row.category_name || "ยังไม่จัดหมวดหมู่"} · {row.symptom_name || "—"}</td>
                <td>{row.frequency}</td>
                <td>{formatDateTime(row.last_reported_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="customer-profile-grid">
        <ContractEditor contract={contract} canEdit={canEdit}
          onSave={(body) => save("/contract", "PATCH", body, "บันทึกสัญญาแล้ว")} />
        <ExamWindows rows={windows} canEdit={canEdit}
          onAdd={(body) => save("/exam-windows", "POST", body, "เพิ่มช่วงสอบแล้ว")}
          onToggle={(row) => save(`/exam-windows/${row.id}`, "PUT",
            { name: row.name, starts_at: row.starts_at, ends_at: row.ends_at, is_active: !row.is_active },
            row.is_active ? "ปิดใช้ช่วงสอบแล้ว" : "เปิดใช้ช่วงสอบแล้ว")} />
        <NamedList title="หน่วยงาน" rows={departments} canEdit={canEdit}
          onAdd={(name) => save("/departments", "POST", { name }, "เพิ่มหน่วยงานแล้ว")} />
        <NamedList title="รายวิชา / การสอบ" rows={courses} canEdit={canEdit} withKind
          onAdd={(name, kind) => save("/courses", "POST", { name, kind }, "เพิ่มรายวิชา/การสอบแล้ว")} />
        {canEdit && (
          <AddContact organizationId={organizationId} onAdded={() => {
            setMessage("เพิ่มผู้ติดต่อแล้ว");
            onContactsChanged();
          }} onError={setError} />
        )}
      </div>
      {error && <p role="alert" className="form-error">{error}</p>}
      {message && <p role="status" className="form-message">{message}</p>}
    </section>
  );
}

function ContractEditor({ contract, canEdit, onSave }: {
  contract: Contract;
  canEdit: boolean;
  onSave: (body: Contract) => Promise<boolean>;
}) {
  const [start, setStart] = useState(contract.contract_start_date ?? "");
  const [end, setEnd] = useState(contract.contract_end_date ?? "");
  useEffect(() => {
    const sync = setTimeout(() => {
      setStart(contract.contract_start_date ?? "");
      setEnd(contract.contract_end_date ?? "");
    }, 0);
    return () => clearTimeout(sync);
  }, [contract]);
  if (!canEdit) return null;
  return (
    <form className="customer-profile-box" onSubmit={(event: FormEvent) => {
      event.preventDefault();
      onSave({ contract_start_date: start || null, contract_end_date: end || null });
    }}>
      <h3>สัญญา</h3>
      <label>วันเริ่มสัญญา<Input type="date" value={start} onChange={setStart} /></label>
      <label>วันสิ้นสุดสัญญา<Input type="date" value={end} onChange={setEnd} /></label>
      <Button type="submit">บันทึกสัญญา</Button>
    </form>
  );
}

function ExamWindows({ rows, canEdit, onAdd, onToggle }: {
  rows: ExamWindow[];
  canEdit: boolean;
  onAdd: (body: { name: string; starts_at: string; ends_at: string }) => Promise<boolean>;
  onToggle: (row: ExamWindow) => Promise<boolean>;
}) {
  const [name, setName] = useState("");
  const [starts, setStarts] = useState("");
  const [ends, setEnds] = useState("");
  return (
    <div className="customer-profile-box">
      <h3>ช่วงสอบจริง (Exam Window)</h3>
      <p className="field-hint">เคสที่ลูกค้าแจ้งในช่วงนี้จะถูกยกระดับความเร่งด่วนขึ้นหนึ่งขั้นอัตโนมัติ</p>
      {rows.length === 0 ? <p className="field-hint">ยังไม่มีช่วงสอบ</p> : (
        <ul className="customer-profile-list">
          {rows.map((row) => (
            <li key={row.id} className={row.is_active ? undefined : "is-inactive"}>
              <span>{row.name} · {formatDateTime(row.starts_at)} – {formatDateTime(row.ends_at)}</span>
              {canEdit && (
                <button type="button" className="text-link" onClick={() => onToggle(row)}>
                  {row.is_active ? "ปิดใช้" : "เปิดใช้"}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
      {canEdit && (
        <form onSubmit={async (event) => {
          event.preventDefault();
          const ok = await onAdd({
            name: name.trim(),
            starts_at: new Date(starts).toISOString(),
            ends_at: new Date(ends).toISOString(),
          });
          if (ok) { setName(""); setStarts(""); setEnds(""); }
        }}>
          <label>ชื่อการสอบ<Input required maxLength={150} value={name} onChange={setName} /></label>
          <label>เริ่ม<Input type="datetime-local" required value={starts} onChange={setStarts} /></label>
          <label>สิ้นสุด<Input type="datetime-local" required value={ends} onChange={setEnds} /></label>
          <Button type="submit" disabled={!name.trim() || !starts || !ends}>เพิ่มช่วงสอบ</Button>
        </form>
      )}
    </div>
  );
}

function NamedList({ title, rows, canEdit, withKind, onAdd }: {
  title: string;
  rows: Named[];
  canEdit: boolean;
  withKind?: boolean;
  onAdd: (name: string, kind?: "course" | "exam") => Promise<boolean>;
}) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState<"course" | "exam">("course");
  return (
    <div className="customer-profile-box">
      <h3>{title}</h3>
      {rows.length === 0 ? <p className="field-hint">ยังไม่มีรายการ</p> : (
        <ul className="customer-profile-list">
          {rows.map((row) => (
            <li key={row.id} className={row.is_active ? undefined : "is-inactive"}>
              {row.name}{row.kind ? ` · ${row.kind === "exam" ? "การสอบ" : "รายวิชา"}` : ""}
            </li>
          ))}
        </ul>
      )}
      {canEdit && (
        <form onSubmit={async (event) => {
          event.preventDefault();
          if (await onAdd(name.trim(), withKind ? kind : undefined)) setName("");
        }}>
          <label>เพิ่ม{title}<Input required maxLength={150} value={name} onChange={setName} /></label>
          {withKind && (
            <label>ประเภท
              <SelectControl value={kind} onValueChange={(next) => setKind(next as "course" | "exam")}>
                <option value="course">รายวิชา</option>
                <option value="exam">การสอบ</option>
              </SelectControl>
            </label>
          )}
          <Button type="submit" disabled={!name.trim()}>เพิ่ม</Button>
        </form>
      )}
    </div>
  );
}

function AddContact({ organizationId, onAdded, onError }: {
  organizationId: number;
  onAdded: () => void;
  onError: (message: string) => void;
}) {
  const [name, setName] = useState("");
  const [channel, setChannel] = useState<string>("email");
  const [value, setValue] = useState("");
  const [saving, setSaving] = useState(false);
  return (
    <form className="customer-profile-box" onSubmit={async (event) => {
      event.preventDefault();
      setSaving(true);
      onError("");
      try {
        const contact = await api<{ id: number }>(`/customers/organizations/${organizationId}/contacts`, {
          method: "POST", body: JSON.stringify({ name: name.trim() }),
        });
        if (value.trim())
          await api(`/customers/contacts/${contact.id}/channels`, {
            method: "POST", body: JSON.stringify({ channel_type: channel, value: value.trim() }),
          });
        setName("");
        setValue("");
        onAdded();
      } catch (e) {
        onError(e instanceof Error ? e.message : "เพิ่มผู้ติดต่อไม่สำเร็จ");
      } finally {
        setSaving(false);
      }
    }}>
      <h3>เพิ่มผู้ติดต่อ</h3>
      <label>ชื่อผู้ติดต่อ<Input required maxLength={150} value={name} onChange={setName} /></label>
      <label>ช่องทางติดต่อ
        <SelectControl value={channel} onValueChange={setChannel}>
          {CHANNELS.map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </SelectControl>
      </label>
      <label>ข้อมูลติดต่อ<Input maxLength={150} value={value} onChange={setValue} /></label>
      <Button type="submit" disabled={saving || !name.trim()}>เพิ่มผู้ติดต่อ</Button>
    </form>
  );
}
