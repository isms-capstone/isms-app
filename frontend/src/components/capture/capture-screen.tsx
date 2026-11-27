"use client";
import { SelectControl, TextArea } from "@/components/ui/company-fields";
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";
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
  Camera,
  X,
} from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import { Button, Input, cx } from "@/components/ui/primitives";
import { api } from "@/lib/api";
import {
  channelNames,
  severityNames,
  type SelectionContext,
  type Ticket as TicketType,
} from "@/lib/types";
import { previewRows } from "@/lib/preview";
import { CustomerPicker } from "./customer-picker";
import {
  SimilarityPanel,
  type ReuseValues,
} from "@/components/cases/similarity-panel";
import {
  CategoryFields,
  emptyCategories,
  type CategoryValues,
} from "@/components/cases/category-fields";
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
type CaptureSnapshot = {
  context: SelectionContext | null;
  subject: string;
  channel: string;
  description: string;
  instance: number | null;
  department: string;
  course: string;
  categories: CategoryValues;
  createdFor: string;
  savedAt?: number;
};
const MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024;
const ATTACHMENT_TYPES = /^(image\/(jpeg|png|webp|gif)|application\/pdf|video\/(mp4|webm)|application\/(zip|gzip|x-gzip|x-zip-compressed))$/;
const ATTACHMENT_EXTENSIONS = /\.(jpe?g|png|webp|gif|pdf|mp4|webm|zip|gz)$/i;

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
    [course, setCourse] = useState("");
  const [categories, setCategories] = useState<CategoryValues>(emptyCategories);
  const [optionsLoading, setOptionsLoading] = useState(false),
    [existing, setExisting] = useState<TicketType[]>([]),
    [error, setError] = useState(""),
    [saving, setSaving] = useState(false),
    [message, setMessage] = useState("");
  const [similarFeedbackId, setSimilarFeedbackId] = useState<number | null>(
    null,
  );
  const [similarBlocked, setSimilarBlocked] = useState(false);
  const [createdFor, setCreatedFor] = useState("");
  const [members, setMembers] = useState<{ id: number; name: string }[]>([]);
  const [files, setFiles] = useState<File[]>([]);
  const savedTicketId = useRef<number | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  // CAP-07: evidence comes from the clipboard, a drag-and-drop or the phone
  // camera as well as the file picker; every path lands in the same list.
  const addFiles = useCallback((incoming: File[]) => {
    const accepted = incoming.filter((file) => ATTACHMENT_TYPES.test(file.type) || ATTACHMENT_EXTENSIONS.test(file.name));
    const tooBig = accepted.filter((file) => file.size > MAX_ATTACHMENT_BYTES);
    const usable = accepted.filter((file) => file.size <= MAX_ATTACHMENT_BYTES);
    if (incoming.length && (accepted.length < incoming.length || tooBig.length))
      setError(
        tooBig.length
          ? `ไฟล์ใหญ่เกิน 25 MB: ${tooBig.map((file) => file.name).join(", ")}`
          : "แนบได้เฉพาะภาพ, MP4, WebM, PDF หรือไฟล์ log แบบ ZIP/GZIP",
      );
    if (!usable.length) return;
    setFiles((current) => [
      ...current,
      ...usable
        .map((file, index) =>
          file.name && file.name !== "image.png"
            ? file
            : new File([file], `screenshot-${Date.now()}-${index + 1}.${file.type.split("/")[1] || "png"}`, { type: file.type }),
        )
        .filter((file) => !current.some((item) => item.name === file.name && item.size === file.size)),
    ]);
  }, []);
  useEffect(() => {
    if (preview) return;
    function onPaste(event: ClipboardEvent) {
      const pasted = Array.from(event.clipboardData?.files ?? []);
      if (!pasted.length) return;
      event.preventDefault();
      addFiles(pasted);
    }
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [preview, addFiles]);
  // CAP-05 (P1-CAP-03): keep the form on this device every 5 seconds, on leaving
  // a field and when the page is hidden, so closing the tab or losing the
  // network never loses what was typed. Files cannot be stored and are re-attached.
  const draftKey = session ? `isms:capture-draft:${session.id}` : null;
  const [restorable, setRestorable] = useState<CaptureSnapshot | null>(null),
    [autosavedAt, setAutosavedAt] = useState<Date | null>(null);
  const snapshot = useMemo<CaptureSnapshot>(
    () => ({ context, subject, channel, description, instance, department, course, categories, createdFor }),
    [context, subject, channel, description, instance, department, course, categories, createdFor],
  );
  const dirty = !!(context || subject.trim() || description.trim() || channel);
  // ADO-01 / CAP-04 evidence: time from the user's first input to saving.
  const startedAt = useRef<number | null>(null);
  useEffect(() => {
    if (dirty && startedAt.current === null) startedAt.current = Date.now();
  }, [dirty]);
  const persist = useCallback(() => {
    if (!draftKey || preview || !dirty || savedTicketId.current) return;
    try {
      localStorage.setItem(draftKey, JSON.stringify({ ...snapshot, savedAt: Date.now() }));
      setAutosavedAt(new Date());
    } catch {
      /* storage unavailable (private mode / quota): nothing else to do */
    }
  }, [draftKey, preview, dirty, snapshot]);
  useEffect(() => {
    if (!draftKey || preview) return;
    // Read after mount (session arrives asynchronously); deferred to avoid a
    // synchronous state update inside the effect.
    const timer = setTimeout(() => {
      try {
        const stored = localStorage.getItem(draftKey);
        if (stored) setRestorable(JSON.parse(stored));
      } catch {
        /* ignore unreadable storage */
      }
    }, 0);
    return () => clearTimeout(timer);
  }, [draftKey, preview]);
  useEffect(() => {
    if (!dirty) return;
    const timer = setTimeout(persist, 5000);
    return () => clearTimeout(timer);
  }, [persist, dirty]);
  useEffect(() => {
    const flush = () => document.visibilityState === "hidden" && persist();
    window.addEventListener("pagehide", persist);
    document.addEventListener("visibilitychange", flush);
    return () => {
      window.removeEventListener("pagehide", persist);
      document.removeEventListener("visibilitychange", flush);
    };
  }, [persist]);
  const forgetDraft = useCallback(() => {
    try {
      if (draftKey) localStorage.removeItem(draftKey);
    } catch {
      /* ignore */
    }
    setRestorable(null);
  }, [draftKey]);
  function restoreDraft(value: CaptureSnapshot) {
    setContext(value.context);
    setSubject(value.subject || "");
    setChannel(value.channel || "");
    setDescription(value.description || "");
    setInstance(value.instance ?? null);
    setDepartment(value.department || "");
    setCourse(value.course || "");
    setCategories(value.categories || emptyCategories);
    setCreatedFor(value.createdFor || "");
    setRestorable(null);
  }
  useEffect(() => {
    if (preview) return;
    const controller = new AbortController();
    api<{ id: number; name: string }[]>("/tickets/team-members", {
      signal: controller.signal,
    })
      .then(setMembers)
      .catch(() => {});
    return () => controller.abort();
  }, [preview]);
  const onSimilarityState = useCallback(
    (id: number | null, blocked: boolean) => {
      setSimilarFeedbackId(id);
      setSimilarBlocked(blocked);
    },
    [],
  );
  const onReuse = useCallback((values: ReuseValues) => {
    setInstance(values.product_instance_id);
    setCategories((current) => ({
      ...current,
      ...values,
      symptom_id: null,
      service_stage_id: null,
    }));
  }, []);
  const onError = useCallback((value: string) => setError(value), []);
  const chooseContext = useCallback((value: SelectionContext | null) => {
    setContext(value);
    setSimilarFeedbackId(null);
    setExisting([]);
    setInstance(value?.instances.length === 1 ? value.instances[0].id : null);
    setDepartment("");
    setCourse("");
    setCategories(emptyCategories);
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
  const complete = !!context && !!subject.trim() && !!channel;
  const selectedProduct = context?.instances.find(
    (item) => item.id === instance,
  );
  async function save(draft: boolean) {
    if (preview) {
      setMessage("หน้านี้เป็นตัวอย่างดีไซน์ ไม่มีการบันทึกข้อมูล");
      return;
    }
    if (!(session?.can_open_cases ?? session?.can_create_cases) || saving || optionsLoading) return;
    if (!savedTicketId.current && !draft && similarBlocked) {
      setError("มีเคสที่คล้ายกัน กรุณาเลือกว่าจะใช้วิธีแก้เดิม ผูกกับเคสเดิม หรือเปิดสอบสวนใหม่ ก่อนสร้างเคส");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const ticketId =
        savedTicketId.current ??
        (
          await api<TicketType>("/tickets", {
            method: "POST",
            body: JSON.stringify({
              save_as_draft: draft,
              similarity_feedback_id: similarFeedbackId,
              capture_seconds:
                startedAt.current === null
                  ? null
                  : Math.round((Date.now() - startedAt.current) / 1000),
              created_for_user_id: createdFor ? Number(createdFor) : null,
              subject,
              description,
              channel: channel || null,
              organization_id: context?.organization.id || null,
              contact_id: context?.contact?.id || null,
              product_instance_id: instance,
              department_id: department ? Number(department) : null,
              course_or_exam_id: course ? Number(course) : null,
              ...categories,
            }),
          })
        ).id;
      savedTicketId.current = ticketId;
      for (const file of files) {
        const body = new FormData();
        body.append("file", file);
        await api(`/tickets/${ticketId}/attachments`, {
          method: "POST",
          body,
        });
        setFiles((remaining) => remaining.filter((item) => item !== file));
      }
      forgetDraft();
      router.push(href(`/cases/${ticketId}`));
    } catch (e) {
      const detail = e instanceof Error ? e.message : "บันทึกเคสไม่สำเร็จ";
      setError(
        savedTicketId.current
          ? `บันทึกเคส #${savedTicketId.current} แล้ว แต่แนบไฟล์ไม่สำเร็จ · ${detail} · กดบันทึกอีกครั้งเพื่อแนบไฟล์ที่เหลือ`
          : detail,
      );
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
      <SelectControl
        value={value}
        disabled={disabled}
        onValueChange={(nextValue) => setValue(nextValue)}
      >
        <option value="">ยังไม่ระบุ</option>
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </SelectControl>
    </label>
  );
  return (
    <AppShell title="สร้างเคส">
      <div className="capture-page">
        <div className="page-heading">
          <div>
            <h1>สร้างเคส</h1>
            <p>
              กรอกแค่ลูกค้า หัวข้อ และช่องทาง ก็สร้างเคสได้ทันที
              รายละเอียดอื่นค่อยเติมทีหลัง
            </p>
          </div>
          <Link className="button button-secondary" href={href("/my-work")}>
            ยกเลิก
          </Link>
        </div>
        {restorable && (
          <div className="restore-banner" role="status">
            <span>
              พบข้อมูลที่กรอกค้างไว้เมื่อ{" "}
              {new Date(restorable.savedAt ?? 0).toLocaleTimeString("th-TH", {
                hour: "2-digit",
                minute: "2-digit",
              })}{" "}
              น.{restorable.subject ? ` · “${restorable.subject}”` : ""} (ไฟล์แนบต้องเลือกใหม่)
            </span>
            <Button variant="primary" size="sm" onClick={() => restoreDraft(restorable)}>
              กู้คืน
            </Button>
            <Button size="sm" onClick={forgetDraft}>
              ทิ้ง
            </Button>
          </div>
        )}
        <form id="create-case-form" onSubmit={onSubmit} onBlur={persist}>
          <div className="capture-layout">
            <section className="surface capture-card">
              <div className="capture-card-heading">
                <h2>
                  ข้อมูลที่ต้องกรอก{" "}
                  <span className="required-chip">3 ช่อง</span>
                </h2>
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
                        placeholder="พิมพ์ชื่อองค์กร ผู้แจ้ง อีเมล หรือ LINE"
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
              <label className="subject-field" htmlFor="case-subject">
                หัวข้อ <span className="required">*</span>
                <Input
                  id="case-subject"
                  aria-label="หัวข้อ *"
                  value={subject}
                  maxLength={255}
                  placeholder="สรุปปัญหาสั้น ๆ เช่น ดาวน์โหลดข้อสอบไม่ได้ทั้งห้องสอบ"
                  onChange={setSubject}
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
                            ? "แก้ไขแล้ว"
                            : index === 1
                              ? "ปิดแล้ว"
                              : "กำลังดำเนินการ"}{" "}
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
                    เป็นเพียงคำแนะนำ ถ้าไม่ใช่เรื่องเดียวกันให้สร้างเคสใหม่ได้เลย
                  </p>
                </section>
              ) : context && existing.length > 0 ? (
                <section className="related-cases">
                  <div className="related-heading">
                    <h3>ลูกค้ารายนี้มีเคสที่ยังเปิดอยู่</h3>
                    <span>{existing.length} เคส · ถ้าเป็นเรื่องเดิมให้เพิ่มในเคสเดิมแทน</span>
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
                        เพิ่มเข้าเคสเดิม
                      </Link>
                    </div>
                  ))}
                </section>
              ) : null}
              {!preview && (
                <SimilarityPanel
                  subject={subject}
                  description={description}
                  organizationId={context?.organization.id || null}
                  instanceId={instance}
                  onState={onSimilarityState}
                  onReuse={onReuse}
                  onReopened={(id) => {
                    forgetDraft();
                    router.push(href(`/cases/${id}`));
                  }}
                />
              )}
              <label>
                บันทึกแทนเพื่อนในทีม (ไม่บังคับ)
                <SelectControl
                  value={createdFor}
                  onValueChange={setCreatedFor}
                  disabled={preview || members.length === 0}
                >
                  <option value="">ไม่ใช่ — ฉันเป็นผู้รับเรื่องเอง</option>
                  {members.map((member) => (
                    <option key={member.id} value={member.id}>
                      {member.name}
                    </option>
                  ))}
                </SelectControl>
              </label>
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
                  <span>(เติมทีหลังได้)</span>
                  <ChevronDown size={15} />
                </summary>
                <div className="capture-optional-fields">
                  {select(
                    "ผลิตภัณฑ์ / ระบบที่ลูกค้าใช้งาน",
                    String(instance || ""),
                    (value) => {
                      setInstance(value ? Number(value) : null);
                      setCategories((current) => ({
                        ...current,
                        module_id: null,
                        category_id: null,
                        symptom_id: null,
                        service_stage_id: null,
                      }));
                    },
                    context?.instances.map((item) => ({
                      id: item.id,
                      name: `${item.name} · ${item.version} · ${item.environment}`,
                    })) || [],
                    !context,
                  )}
                  {!preview && (
                    <p className="field-hint full-width">
                      {!context
                        ? "เลือกลูกค้า / ผู้แจ้งก่อน จึงจะเลือกระบบที่ลูกค้าใช้งานได้"
                        : !context.instances.length
                          ? "ลูกค้านี้ยังไม่มีผลิตภัณฑ์ / ระบบที่ผูกไว้ ให้ผู้ดูแลระบบเพิ่มระบบของลูกค้าก่อน"
                          : "เลือกระบบที่ต้องการจัดหมวดหมู่จากรายการของลูกค้า"}
                    </p>
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
                  <div className="full-width">
                    <CategoryFields
                      key={`${instance}-${context?.organization.id}`}
                      productId={selectedProduct?.product_id || null}
                      organizationId={context?.organization.id}
                      departmentId={department ? Number(department) : null}
                      value={categories}
                      onChange={setCategories}
                      preview={preview}
                      onLoading={setOptionsLoading}
                    />
                  </div>
                  <label className="full-width">
                    รายละเอียดปัญหา
                    <TextArea
                      value={description}
                      maxLength={20000}
                      rows={4}
                      onValueChange={(nextValue) => setDescription(nextValue)}
                      placeholder="อธิบายปัญหาและข้อมูลเพิ่มเติม..."
                    />
                  </label>
                </div>
              </details>
              <details className="capture-accordion" open>
                <summary>
                  <ImagePlus size={15} />
                  <strong>ไฟล์แนบหลักฐาน</strong>
                  <span>ไม่บังคับ</span>
                  <ChevronDown size={15} />
                </summary>
                <div className="capture-attachments">
                  <p id="capture-attachment-hint" className="field-hint">
                    รองรับภาพ, MP4, WebM, PDF และไฟล์ log แบบ ZIP/GZIP
                    ขนาดไม่เกิน 25 MB ต่อไฟล์
                  </p>
                  <input
                    ref={fileInput}
                    type="file"
                    accept="image/jpeg,image/png,image/webp,image/gif,application/pdf,.mp4,.webm,.zip,.gz"
                    multiple
                    hidden
                    disabled={preview || saving}
                    onChange={(event) => {
                      addFiles(Array.from(event.target.files ?? []));
                      event.target.value = "";
                    }}
                  />
                  <input
                    ref={cameraInput}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    hidden
                    disabled={preview || saving}
                    onChange={(event) => {
                      addFiles(Array.from(event.target.files ?? []));
                      event.target.value = "";
                    }}
                  />
                  <div
                    className={cx("capture-attachment-picker capture-dropzone", dragging && "is-dragging")}
                    onDragOver={(event) => {
                      event.preventDefault();
                      setDragging(true);
                    }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={(event) => {
                      event.preventDefault();
                      setDragging(false);
                      if (!preview && !saving) addFiles(Array.from(event.dataTransfer.files));
                    }}
                  >
                    <Button
                      type="button"
                      aria-describedby="capture-attachment-hint"
                      disabled={preview || saving}
                      onClick={() => fileInput.current?.click()}
                    >
                      เลือกไฟล์
                    </Button>
                    <Button
                      type="button"
                      disabled={preview || saving}
                      onClick={() => cameraInput.current?.click()}
                    >
                      <Camera size={15} aria-hidden="true" /> ถ่ายภาพ
                    </Button>
                    <span className="field-hint">หรือลากไฟล์มาวาง / กด Ctrl+V วางภาพหน้าจอ</span>
                    <span role="status" className="field-hint">
                      {files.length
                        ? `เลือกแล้ว ${files.length} ไฟล์`
                        : "ยังไม่ได้เลือกไฟล์"}
                    </span>
                  </div>
                  {files.length > 0 && (
                    <ul
                      className="capture-attachment-list"
                      aria-label="ไฟล์ที่เลือก"
                    >
                      {files.map((file, index) => (
                        <li key={`${file.name}-${index}`}>
                          <FileText size={16} aria-hidden="true" />
                          <span>{file.name}</span>
                          <button
                            type="button"
                            className="capture-attachment-remove"
                            aria-label={`เอา ${file.name} ออก`}
                            disabled={saving}
                            onClick={() => setFiles((current) => current.filter((item) => item !== file))}
                          >
                            <X size={14} aria-hidden="true" />
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
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
                  สรุปเคสก่อนบันทึก
                </h2>
                <span>
                  <Clock3 size={11} />
                  ยังไม่บันทึก
                </span>
              </div>
              <dl>
                <dt>เลขเคส</dt>
                <dd className="preview-case-number">
                  {preview ? "DVHT-202609-00425" : "ออกให้เมื่อกดสร้างเคส"}
                  <Clipboard size={14} aria-hidden="true" />
                </dd>
                <dd className="preview-number-hint">
                  {preview
                    ? "เลขตัวอย่างสำหรับตรวจแบบ"
                    : "เคสร่างยังไม่ได้เลขเคส"}
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
                <dt>ความรุนแรง / SLA</dt>
                <dd>
                  {categories.severity
                    ? `${categories.severity} ${severityNames[categories.severity] || ""}`
                    : categories.impact_scope
                      ? "ระบบเสนอจากขอบเขตผลกระทบ"
                      : "ยังไม่ระบุ · SLA เริ่มนับเมื่อระบุขอบเขตผลกระทบในรายละเอียดเพิ่มเติม"}
                </dd>
              </dl>
              <div className="automatic-fields">
                <strong>
                  <CheckCircle2 size={13} />
                  ระบบบันทึกให้อัตโนมัติ
                </strong>
                {[
                  "เลขเคส",
                  "ผู้บันทึก",
                  "วันเวลาที่บันทึก",
                  "สถานะ: ใหม่",
                  "เวลาที่ลูกค้าแจ้ง (แก้ย้อนหลังได้ 7 วัน)",
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
                  <span className="priority-pill priority-S2">S2 สูง</span>
                  <p>ข้อมูลตัวอย่างสำหรับตรวจแบบ</p>
                </div>
              )}
            </aside>
          </div>
        </form>
        <footer className="capture-bottom-bar">
          <span>
            {autosavedAt && (
              <small className="autosave-note">
                บันทึกอัตโนมัติในเครื่องนี้{" "}
                {autosavedAt.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                {" · "}
              </small>
            )}
            {complete ? (
              <>
                <CheckCircle2 size={14} />
                ข้อมูลครบแล้ว กดสร้างเคสได้
              </>
            ) : (
              <>
                ยังขาด: <strong>{[!context && "ลูกค้า", !subject.trim() && "หัวข้อ", !channel && "ช่องทาง"].filter(Boolean).join(", ")}</strong>
              </>
            )}
          </span>
          <div>
            <Button
              disabled={saving || optionsLoading || !(session?.can_open_cases ?? session?.can_create_cases)}
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
                similarBlocked ||
                !(session?.can_open_cases ?? session?.can_create_cases)
              }
            >
              <Plus size={15} />
              {saving ? "กำลังบันทึก…" : "สร้างเคส"}
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
