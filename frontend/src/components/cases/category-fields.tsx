"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Input } from "@/components/ui/primitives";

export type CategoryValues = {
  module_id: number | null;
  category_id: number | null;
  symptom_id: number | null;
  service_stage_id: number | null;
  ticket_type_id: number | null;
  impact_scope: string | null;
  is_exam_window: boolean | null;
  severity: string | null;
  severity_overridden_reason: string | null;
  root_cause_code_id: number | null;
  root_cause_detail: string | null;
  resolution_code_id: number | null;
  resolution_detail: string | null;
  tags: string[];
};
export const emptyCategories: CategoryValues = {
  module_id: null, category_id: null, symptom_id: null, service_stage_id: null,
  ticket_type_id: null, impact_scope: null, is_exam_window: null, severity: null,
  severity_overridden_reason: null, root_cause_code_id: null, root_cause_detail: null,
  resolution_code_id: null, resolution_detail: null, tags: [],
};
type Option = { id: number; name: string; module_id?: number; code?: string };
type Options = { modules: Option[]; problem_types: Option[]; symptoms: Option[]; service_stages: Option[]; ticket_types: Option[]; causes: Option[]; solutions: Option[] };
type Masters = { ticket_types: Option[]; causes: Option[]; solutions: Option[] };
const impacts = [
  { id: "organization", name: "ทั้งองค์กร / ทั้งห้องสอบ" },
  { id: "group", name: "บางกลุ่ม / บางรายวิชา" },
  { id: "single_user", name: "ผู้ใช้รายเดียว" },
  { id: "non_disruptive", name: "คำถาม / คำขอที่ไม่กระทบการใช้งาน" },
];

// Open, then choose. No nested menus or confirmation tap on mobile.
export function CategorySelect({ label, value, options, onChange, disabled = false }: {
  label: string; value: string | number | null; options: { id: string | number; name: string }[];
  onChange: (value: string) => void; disabled?: boolean;
}) {
  const ref = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    function outside(event: PointerEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) ref.current.open = false;
    }
    document.addEventListener("pointerdown", outside);
    return () => document.removeEventListener("pointerdown", outside);
  }, []);
  return <div className="category-select">
    <span className="category-label">{label}</span>
    <details ref={ref} onKeyDown={(event) => {
      if (event.key === "Escape" && ref.current) { ref.current.open = false; ref.current.querySelector("summary")?.focus(); }
    }}>
      <summary aria-label={label} aria-disabled={disabled} onClick={(event) => { if (disabled) event.preventDefault(); }}>
        {options.find((option) => String(option.id) === String(value))?.name || (value ? `ค่าเดิม #${value}` : "ยังไม่ระบุ")}<span aria-hidden="true">⌄</span>
      </summary>
      {!disabled && <div className="category-choices" role="group" aria-label={`ตัวเลือก${label}`}>
        {[{ id: "", name: "ยังไม่ระบุ" }, ...options].map((option) => <button key={option.id} type="button"
          aria-pressed={String(option.id) === String(value ?? "")}
          onClick={() => { onChange(String(option.id)); if (ref.current) { ref.current.open = false; ref.current.querySelector("summary")?.focus(); } }}>
          {option.name}
        </button>)}
      </div>}
    </details>
  </div>;
}

export function CategoryFields({ productId, organizationId, departmentId, value, onChange, preview = false, readOnly = false, onLoading }: {
  productId: number | null; organizationId?: number | null; departmentId?: number | null;
  value: CategoryValues; onChange: (value: CategoryValues) => void;
  preview?: boolean; readOnly?: boolean; onLoading?: (loading: boolean) => void;
}) {
  const [options, setOptions] = useState<Options | null>(null);
  const [masters, setMasters] = useState<Masters | null>(null);
  const [error, setError] = useState("");
  const [suggestion, setSuggestion] = useState<string | null>(null);
  const [tag, setTag] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (preview) return;
    const controller = new AbortController();
    onLoading?.(true);
    Promise.all([
      api<Masters>("/categorization/options", { signal: controller.signal }),
      productId ? api<Options>(`/products/${productId}/categorization-options`, { signal: controller.signal }) : Promise.resolve(null),
    ]).then(([master, scoped]) => { setMasters(master); setOptions(scoped); setError(""); })
      .catch((e) => { if (!controller.signal.aborted) setError(e.message); })
      .finally(() => { if (!controller.signal.aborted) onLoading?.(false); });
    return () => controller.abort();
  }, [productId, preview, onLoading, retry]);
  useEffect(() => {
    if (!value.impact_scope || preview) return;
    const controller = new AbortController();
    const query = new URLSearchParams({ impact_scope: value.impact_scope });
    if (value.is_exam_window !== null) query.set("is_exam_window", String(value.is_exam_window));
    if (organizationId) query.set("organization_id", String(organizationId));
    if (departmentId) query.set("department_id", String(departmentId));
    api<{ severity: string }>(`/categorization/severity-suggestion?${query}`, { signal: controller.signal })
      .then((result) => setSuggestion(result.severity))
      .catch((e) => { if (!controller.signal.aborted) setError(e.message); });
    return () => controller.abort();
  }, [value.impact_scope, value.is_exam_window, organizationId, departmentId, preview]);
  function field(key: keyof CategoryValues, label: string, rows: Option[], disabled = false) {
    return <CategorySelect key={key} label={label} value={value[key] as number | null} options={rows} disabled={disabled || preview || readOnly}
      onChange={(next) => onChange({ ...value, [key]: next ? Number(next) : null,
        ...(key === "module_id" ? { category_id: null } : {}) })} />;
  }
  function addTag() {
    const next = tag.normalize("NFC").trim().toLowerCase();
    if (next && next.length <= 64 && value.tags.length < 20 && !value.tags.includes(next)) {
      onChange({ ...value, tags: [...value.tags, next] }); setTag("");
    }
  }
  const suggested = value.impact_scope ? suggestion : null;
  const override = !!value.severity && !!suggested && value.severity !== suggested;
  return <div className="category-fields">
    <div className="category-grid">
      {field("ticket_type_id", "ประเภทเคส", options?.ticket_types || masters?.ticket_types || [])}
      {field("module_id", "โมดูล (Module)", options?.modules || [], !productId || !options)}
      {field("symptom_id", "อาการ", options?.symptoms || [], !productId || !options)}
      {field("service_stage_id", "ช่วงเวลาของการสอบ", options?.service_stages || [], !productId || !options)}
      {field("category_id", "ประเภทปัญหา", options?.problem_types.filter((row) => row.module_id === value.module_id) || [], !value.module_id)}
    </div>
    <p className="field-hint">โมดูล อาการ และช่วงเวลาของการสอบแยกกัน · ตัวเลือกที่คุณบันทึกบ่อยแสดงก่อน</p>
    {masters?.ticket_types.find((row) => row.id === value.ticket_type_id)?.name === "Request" &&
      <p className="form-message">เส้นทางคำขอบริการ: รับคำขอ → ดำเนินคำขอ → ส่งมอบผล → ยืนยันและปิดคำขอ</p>}
    <div className="category-grid">
      <CategorySelect label="ขอบเขตผลกระทบ" value={value.impact_scope} options={impacts} disabled={preview || readOnly}
        onChange={(impact) => onChange({ ...value, impact_scope: impact || null, severity: null, severity_overridden_reason: null })} />
      <label>ช่วงเวลาที่เกิดเหตุ<select value={value.is_exam_window === null ? "auto" : String(value.is_exam_window)} disabled={preview}
        onChange={(e) => onChange({ ...value, is_exam_window: e.target.value === "auto" ? null : e.target.value === "true", severity: null, severity_overridden_reason: null })}>
        <option value="auto">ใช้ปฏิทินสอบของลูกค้า</option><option value="true">ระหว่างสอบจริง</option><option value="false">นอกช่วงสอบ</option>
      </select></label>
      <label>Severity<select disabled={!value.impact_scope || preview} value={value.severity || ""}
        onChange={(e) => onChange({ ...value, severity: e.target.value || null, severity_overridden_reason: null })}>
        <option value="">ใช้ค่าที่ระบบเสนอ{suggested ? ` (${suggested})` : ""}</option>
        {["S1", "S2", "S3", "S4"].map((severity) => <option key={severity}>{severity}</option>)}
      </select></label>
      <label>เหตุผลที่ปรับ Severity{override && " *"}<Input value={value.severity_overridden_reason || ""} required={override} maxLength={2000}
        onChange={(reason) => onChange({ ...value, severity_overridden_reason: reason })} disabled={preview} /></label>
      {field("root_cause_code_id", "รหัสสาเหตุ", (options?.causes || masters?.causes || []).map((row) => ({ ...row, name: `${row.code} · ${row.name}` })))}
      <label>คำอธิบายสาเหตุ<textarea maxLength={20000} value={value.root_cause_detail || ""} disabled={preview}
        onChange={(e) => onChange({ ...value, root_cause_detail: e.target.value })} /></label>
      {field("resolution_code_id", "รหัสวิธีแก้", (options?.solutions || masters?.solutions || []).map((row) => ({ ...row, name: `${row.code} · ${row.name}` })))}
      <label>คำอธิบายวิธีแก้<textarea maxLength={20000} value={value.resolution_detail || ""} disabled={preview}
        onChange={(e) => onChange({ ...value, resolution_detail: e.target.value })} /></label>
    </div>
    <div className="tag-editor"><label>แท็กอิสระ<Input value={tag} maxLength={64} disabled={preview || value.tags.length >= 20} onChange={setTag}
      onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); addTag(); } }} /></label>
      <button type="button" className="button" onClick={addTag} disabled={preview || !tag.trim() || value.tags.length >= 20}>เพิ่มแท็ก</button></div>
    <div className="tag-list">{value.tags.map((name) => <button type="button" key={name} disabled={preview} aria-label={`ลบแท็ก ${name}`}
      onClick={() => onChange({ ...value, tags: value.tags.filter((item) => item !== name) })}>{name} ×</button>)}</div>
    {error && <p role="alert" className="form-error">{error} <button type="button" onClick={() => setRetry((n) => n + 1)}>โหลดหมวดหมู่อีกครั้ง</button></p>}
  </div>;
}
