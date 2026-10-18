"use client";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Building2,
  Check,
  CheckCircle2,
  ChevronDown,
  Clipboard,
  Clock3,
  Eye,
  ImagePlus,
  MessageCircle,
  Phone,
  Mail,
  Globe,
  Users,
  MoreHorizontal,
  FileText,
  UserRound,
  Ticket,
  Plus,
} from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import { Button, Input, cx } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import {
  channelNames,
  type SelectionContext,
  type Ticket as TicketType,
} from "@/lib/types";
import { previewRows } from "@/lib/preview";
import { CustomerPicker } from "./customer-picker";
const previewContext: SelectionContext = {
  organization: { id: 2, name: "Fammed · เวชศาสตร์ครอบครัว", is_active: true },
  contact: { id: 2, name: "อ.นนท์" },
  instances: [
    {
      id: 1,
      name: "ExamPlus",
      product_id: 1,
      version: "2.4",
      environment: "production",
    },
  ],
  departments: [{ id: 1, name: "ภาควิชาเวชศาสตร์ครอบครัว" }],
  courses: [],
};
type Option = { id: number; name: string; module_id?: number };
type CaseOptions = {
  modules: Option[];
  problem_types: Option[];
  symptoms: Option[];
  service_stages: Option[];
};
export function CaptureScreen() {
  const { session, preview, href } = useSession();
  const router = useRouter();
  const [context, setContext] = useState<SelectionContext | null>(
      preview ? previewContext : null,
    ),
    [subject, setSubject] = useState(
      preview ? "กดเริ่มการสอบ MEQ ไม่ได้ ขึ้นว่า You’re late" : "",
    ),
    [channel, setChannel] = useState(preview ? "line_oa" : ""),
    [description, setDescription] = useState(""),
    [instance, setInstance] = useState<number | null>(preview ? 1 : null);
  const [department, setDepartment] = useState(""),
    [course, setCourse] = useState(""),
    [moduleId, setModuleId] = useState(""),
    [category, setCategory] = useState(""),
    [symptom, setSymptom] = useState(""),
    [stage, setStage] = useState("");
  const [options, setOptions] = useState<CaseOptions | null>(null),
    [optionsLoading, setOptionsLoading] = useState(false),
    [existing, setExisting] = useState<TicketType[]>([]),
    [error, setError] = useState(""),
    [saving, setSaving] = useState(false),
    [message, setMessage] = useState("");
  const onError = useCallback((value: string) => setError(value), []);
  const chooseContext = useCallback((value: SelectionContext | null) => {
    setContext(value);
    setExisting([]);
    setInstance(value?.instances.length === 1 ? value.instances[0].id : null);
    setDepartment("");
    setCourse("");
    setModuleId("");
    setCategory("");
    setSymptom("");
    setStage("");
    setOptions(null);
    setError("");
  }, []);
  useEffect(() => {
    if (!context || preview) return;
    const controller = new AbortController();
    api<TicketType[]>(
      `/tickets?organization_id=${context.organization.id}&open_only=true&limit=5`,
      { signal: controller.signal },
    )
      .then(setExisting)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [context, preview]);
  useEffect(() => {
    if (!instance || !context || preview) return;
    const selected = context.instances.find((item) => item.id === instance);
    if (!selected) return;
    const controller = new AbortController();
    const load = async () => {
      setOptionsLoading(true);
      try {
        const result = await api<CaseOptions>(
          `/products/${selected.product_id}/case-options`,
          { signal: controller.signal },
        );
        setOptions(result);
      } catch (e) {
        if (!controller.signal.aborted)
          setError(e instanceof Error ? e.message : "โหลดหมวดหมู่ไม่สำเร็จ");
      } finally {
        if (!controller.signal.aborted) setOptionsLoading(false);
      }
    };
    load();
    return () => controller.abort();
  }, [instance, context, preview]);
  const complete = !!context && !!subject.trim() && !!channel;
  const selectedProduct = context?.instances.find(
    (item) => item.id === instance,
  );
  async function save(draft: boolean) {
    if (preview) {
      setMessage("หน้านี้เป็น Design Preview · ไม่มีการบันทึกข้อมูลตัวอย่าง");
      return;
    }
    if (!session?.can_create_cases || saving || optionsLoading) return;
    setSaving(true);
    setError("");
    try {
      const ticket = await api<TicketType>("/tickets", {
        method: "POST",
        body: JSON.stringify({
          save_as_draft: draft,
          subject,
          description,
          channel: channel || null,
          organization_id: context?.organization.id || null,
          contact_id: context?.contact?.id || null,
          product_instance_id: instance,
          department_id: department ? Number(department) : null,
          course_or_exam_id: course ? Number(course) : null,
          module_id: moduleId ? Number(moduleId) : null,
          category_id: category ? Number(category) : null,
          symptom_id: symptom ? Number(symptom) : null,
          service_stage_id: stage ? Number(stage) : null,
        }),
      });
      router.push(href(`/cases/${ticket.id}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกเคสไม่สำเร็จ");
    } finally {
      setSaving(false);
    }
  }
  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    save(false);
  };
  const select = (
    title: string,
    value: string,
    setValue: (value: string) => void,
    items: Option[],
    disabled = false,
  ) => (
    <label>
      {title}
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
      >
        <option value="">ยังไม่ระบุ</option>
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </select>
    </label>
  );
  return (
    <AppShell title="สร้างเคส">
      <div className="capture-page">
        <div className="page-heading">
          <div>
            <h1>สร้างเคส</h1>
            <p>บันทึกเรื่องก่อน แล้วค่อยเติมรายละเอียดภายหลัง</p>
            <small>
              <strong>สร้างเคสด้วยข้อมูลขั้นต่ำ 3 ช่อง</strong>{" "}
              <span>รายละเอียดอื่นสามารถเติมภายหลังได้</span>
            </small>
          </div>
          <Link className="button button-secondary" href={href("/my-work")}>
            ยกเลิก
          </Link>
        </div>
        <form id="create-case-form" onSubmit={onSubmit}>
          <div className="capture-layout">
            <section className="surface capture-card">
              <div className="capture-card-heading">
                <h2>
                  ข้อมูลเริ่มต้น{" "}
                  <span className="required-chip">ต้องกรอก 3 ช่อง</span>
                </h2>
                <small>3 required fields</small>
              </div>
              {preview ? (
                <div className="customer-picker">
                  <label>
                    ลูกค้า / ผู้แจ้ง <span className="required">*</span>
                  </label>
                  <div className="customer-picker-row">
                    <div className="search-field">
                      <SearchIcon />
                      <Input
                        placeholder="ค้นหาลูกค้าหรือผู้แจ้ง..."
                        aria-label="ค้นหาลูกค้าหรือผู้แจ้ง"
                      />
                    </div>
                    <div className="selected-customer">
                      <span className="customer-square">
                        <Building2 size={21} />
                      </span>
                      <span>
                        <strong>{previewContext.organization.name}</strong>
                        <small>{previewContext.contact?.name} · LINE OA</small>
                      </span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          setMessage("ข้อมูลตัวอย่างสำหรับตรวจดีไซน์")
                        }
                      >
                        เปลี่ยน
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                <CustomerPicker
                  value={context}
                  onChange={chooseContext}
                  onError={onError}
                />
              )}
              <label className="subject-field">
                หัวข้อ <span className="required">*</span>
                <Input
                  value={subject}
                  maxLength={255}
                  placeholder="ระบุเรื่องที่ต้องการแจ้งให้เข้าใจง่าย"
                  onChange={(e) => setSubject(e.target.value)}
                />
              </label>
              {preview ? (
                <section className="related-cases">
                  <div className="related-heading">
                    <h3>เคสที่คล้ายกัน</h3>
                    <span>พบ 3 รายการ</span>
                    <small>ตัวอย่างการแสดงผล</small>
                  </div>
                  {previewRows.slice(0, 3).map((row, index) => (
                    <div className="related-case" key={row.id}>
                      <span className="match-score">
                        {[94, 91, 78][index]}%
                      </span>
                      <div className="related-number">{row.ticket_no}</div>
                      <div className="related-subject">
                        <strong>{row.subject}</strong>
                        <small>
                          {row.product} ·{" "}
                          {index === 0
                            ? "Resolved"
                            : index === 1
                              ? "Closed"
                              : "In Progress"}{" "}
                          · {row.assignee} · {row.customer.split(" · ")[0]}
                        </small>
                      </div>
                      <Link
                        href={href(`/cases/${row.id}`)}
                        className="button button-secondary button-sm"
                      >
                        <Eye size={12} />
                        ดูเคส
                      </Link>
                    </div>
                  ))}
                  <p>
                    เคสที่คล้ายกันเป็นเพียงคำแนะนำ คุณยังสามารถสร้างเคสใหม่ได้
                  </p>
                </section>
              ) : context && existing.length > 0 ? (
                <section className="related-cases">
                  <div className="related-heading">
                    <h3>เคสเปิดของลูกค้ารายนี้</h3>
                    <span>{existing.length} รายการล่าสุด</span>
                  </div>
                  {existing.map((row) => (
                    <div className="existing-case" key={row.id}>
                      <span>
                        <small>{row.ticket_no}</small>
                        <strong>{row.subject}</strong>
                      </span>
                      <Link
                        className="button button-secondary button-sm"
                        href={href(`/cases/${row.id}`)}
                      >
                        ดูเคสเดิม
                      </Link>
                    </div>
                  ))}
                </section>
              ) : null}
              <fieldset className="channel-field">
                <legend>
                  ช่องทาง <span className="required">*</span>
                </legend>
                <div className="channel-options">
                  {Object.entries(channelNames).map(([id, label]) => {
                    const Icon = id.startsWith("line")
                      ? MessageCircle
                      : id === "phone"
                        ? Phone
                        : id === "email"
                          ? Mail
                          : id === "portal"
                            ? Globe
                            : id === "face_to_face"
                              ? Users
                              : MoreHorizontal;
                    return (
                      <button
                        type="button"
                        key={id}
                        className={cx(
                          "channel-option",
                          channel === id && "active",
                        )}
                        aria-pressed={channel === id}
                        onClick={() => setChannel(id)}
                      >
                        <Icon size={14} />
                        {label}
                      </button>
                    );
                  })}
                </div>
              </fieldset>
              <details className="capture-accordion">
                <summary>
                  <FileText size={15} />
                  <strong>รายละเอียดเพิ่มเติม</strong>
                  <span>(ไม่จำเป็นต้องกรอกตอนนี้)</span>
                  <ChevronDown size={15} />
                </summary>
                <div className="capture-optional-fields">
                  {select(
                    "ผลิตภัณฑ์ / ระบบที่ลูกค้าใช้งาน",
                    String(instance || ""),
                    (value) => {
                      setInstance(value ? Number(value) : null);
                      setModuleId("");
                      setCategory("");
                      setSymptom("");
                      setStage("");
                      setOptions(null);
                    },
                    context?.instances.map((item) => ({
                      id: item.id,
                      name: `${item.name} · ${item.version} · ${item.environment}`,
                    })) || [],
                    !context,
                  )}
                  {select(
                    "โมดูล (Module)",
                    moduleId,
                    (value) => {
                      setModuleId(value);
                      setCategory("");
                    },
                    options?.modules || [],
                    !options,
                  )}
                  {select(
                    "หน่วยงาน / ภาควิชา",
                    department,
                    setDepartment,
                    context?.departments || [],
                    !context,
                  )}
                  {select(
                    "รายวิชา / การสอบ",
                    course,
                    setCourse,
                    context?.courses || [],
                    !context,
                  )}
                  {select(
                    "ประเภทปัญหา",
                    category,
                    setCategory,
                    options?.problem_types.filter(
                      (item) => item.module_id === Number(moduleId),
                    ) || [],
                    !moduleId,
                  )}
                  {select(
                    "อาการ",
                    symptom,
                    setSymptom,
                    options?.symptoms || [],
                    !options,
                  )}
                  {select(
                    "ช่วงบริการ",
                    stage,
                    setStage,
                    options?.service_stages || [],
                    !options,
                  )}
                  <label className="full-width">
                    รายละเอียดปัญหา
                    <textarea
                      value={description}
                      maxLength={20000}
                      rows={4}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="อธิบายปัญหาและข้อมูลเพิ่มเติม..."
                    />
                  </label>
                </div>
              </details>
              <details className="capture-accordion attachment-accordion">
                <summary>
                  <ImagePlus size={15} />
                  <strong>หลักฐาน</strong>
                  <span>แนบภาพหรือไฟล์เพื่อช่วยตรวจสอบปัญหา</span>
                  <ChevronDown size={15} />
                </summary>
                <p className="field-hint">
                  ส่วนแนบไฟล์ยังไม่เปิดใช้งานใน Backend รอบนี้
                </p>
              </details>
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              {message && (
                <p className="form-message" role="status">
                  {message}
                </p>
              )}
            </section>
            <aside className="surface case-preview">
              <div className="case-preview-heading">
                <h2>
                  <Ticket size={15} />
                  ตัวอย่างเคส
                </h2>
                <span>
                  <Clock3 size={11} />
                  DRAFT / ยังไม่สร้าง
                </span>
              </div>
              <dl>
                <dt>เลขที่เคส</dt>
                <dd className="preview-case-number">
                  {preview ? "DVHT-202609-00425" : "ระบบออกเลขหลังสร้างเคส"}
                  <Clipboard size={14} aria-hidden="true" />
                </dd>
                <dd className="preview-number-hint">
                  {preview
                    ? "เลขตัวอย่างสำหรับตรวจแบบ"
                    : "ไม่จองเลขเคสก่อนบันทึกจริง"}
                </dd>
                <dt>ลูกค้า</dt>
                <dd className="preview-customer">
                  <Building2 size={17} />
                  {context?.organization.name || "ยังไม่เลือกลูกค้า"}
                </dd>
                <dt>ผู้แจ้ง</dt>
                <dd>
                  <UserRound size={14} />
                  {context?.contact?.name || "ยังไม่ระบุ"}
                </dd>
                <dt>ช่องทาง</dt>
                <dd>
                  {channel && <MessageCircle size={14} />}{" "}
                  {channelNames[channel] || "ยังไม่ระบุ"}
                </dd>
                <dt>หัวข้อ</dt>
                <dd>{subject || "ยังไม่ระบุหัวข้อ"}</dd>
                <dt>ผลิตภัณฑ์</dt>
                <dd>{selectedProduct?.name || "ยังไม่ระบุ"}</dd>
              </dl>
              <div className="automatic-fields">
                <strong>
                  <CheckCircle2 size={13} />
                  ระบบจะบันทึกให้หลังสร้างเคส
                </strong>
                {[
                  "เลขที่เคส (เมื่อส่งเป็น New)",
                  "ผู้สร้าง / ผู้แจ้ง",
                  "วันที่สร้าง",
                  "สถานะเริ่มต้น",
                  "วันที่แจ้ง",
                ].map((text) => (
                  <span key={text}>
                    <Check size={12} />
                    {text}
                  </span>
                ))}
              </div>
              {preview && (
                <div className="preview-priority">
                  <strong>ความรุนแรงที่ระบบเสนอ</strong>
                  <span className="priority-pill priority-S2">S2 High</span>
                  <p>ตัวอย่างหน้าตา · ยังไม่มีระบบเสนอความรุนแรงใน Backend</p>
                </div>
              )}
            </aside>
          </div>
        </form>
        <footer className="capture-bottom-bar">
          <span>
            {complete ? (
              <>
                <CheckCircle2 size={14} />
                ข้อมูลครบ 3 ช่องแล้ว
              </>
            ) : (
              <>
                ต้องกรอก: <strong>ลูกค้า / ผู้แจ้ง, หัวข้อ, ช่องทาง</strong>
              </>
            )}
          </span>
          <div>
            <Button
              disabled={saving || optionsLoading || !session?.can_create_cases}
              onClick={() => save(true)}
            >
              บันทึกเป็นร่าง
            </Button>
            <Button
              form="create-case-form"
              type="submit"
              variant="primary"
              disabled={
                saving ||
                optionsLoading ||
                !complete ||
                !session?.can_create_cases
              }
            >
              <Plus size={15} />
              {saving ? "กำลังบันทึก..." : "สร้างเคส"}
            </Button>
          </div>
        </footer>
      </div>
    </AppShell>
  );
}
function SearchIcon() {
  return (
    <span className="search-symbol" aria-hidden="true">
      ⌕
    </span>
  );
}
