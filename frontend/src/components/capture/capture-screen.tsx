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

type SimilarCase = {
  id: number;
  ticket_no: string | null;
  subject: string | null;
  status: string;
  hint: string;
  score: number;
  customer: string;
  product: string;
  assignee: string | null;
  last_activity: string;
  channel?: string | null;
  category_id?: number | null;
  product_instance_id?: number | null;
  severity?: string | null;
  resolution_code_id?: number | null;
  resolution_detail?: string | null;
};

type SimilarSearchResponse = {
  feedback_id: number | null;
  count: number;
  items: SimilarCase[];
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
    const [files, setFiles] = useState<File[]>([]);
  const [options, setOptions] = useState<CaseOptions | null>(null),
    [optionsLoading, setOptionsLoading] = useState(false),
    [existing, setExisting] = useState<TicketType[]>([]),
    [error, setError] = useState(""),
    [saving, setSaving] = useState(false),
    [message, setMessage] = useState("");
  const [similarItems, setSimilarItems] = useState<SimilarCase[]>([]);
const [similarFeedbackId, setSimilarFeedbackId] = useState<number | null>(null);
const [similarLoading, setSimilarLoading] = useState(false);
const [similarError, setSimilarError] = useState("");
const [similarRetry, setSimilarRetry] = useState(0);
const [similarDecision, setSimilarDecision] = useState<
  "reuse" | "link" | "new" | ""
>("");
const [chosenSimilarId, setChosenSimilarId] = useState<number | null>(null);
const [decisionSaving, setDecisionSaving] = useState(false);
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
  const similarityQuery = `${subject} ${description}`.trim();

useEffect(() => {
  if (preview || !session || similarityQuery.length < 10) {
    setSimilarItems([]);
    setSimilarFeedbackId(null);
    setSimilarError("");
    setSimilarLoading(false);
    return;
  }

  const controller = new AbortController();

  const debounceTimer = window.setTimeout(async () => {
  const timeoutTimer = window.setTimeout(() => {
  if (!controller.signal.aborted) {
    setSimilarError("ค้นหาเคสใช้เวลานานเกินไป กรุณาลองอีกครั้ง");
    setSimilarLoading(false);
    controller.abort();
  }
}, 10000);

    setSimilarLoading(true);
    setSimilarError("");

    try {
      const params = new URLSearchParams({
        q: similarityQuery,
      });

      if (context?.organization.id) {
        params.set("organization_id", String(context.organization.id));
      }

      if (instance) {
        params.set("product_instance_id", String(instance));
      }

      const result = await api<SimilarSearchResponse>(
        `/tickets/similar?${params.toString()}`,
        { signal: controller.signal },
      );

      if (!controller.signal.aborted) {
        setSimilarItems(result.items || []);
        setSimilarFeedbackId(result.feedback_id);
        setSimilarDecision("");
        setChosenSimilarId(null);
      }
    } catch (e) {
      if (!controller.signal.aborted) {
        setSimilarError(
          e instanceof Error ? e.message : "ค้นหาเคสคล้ายไม่สำเร็จ",
        );
      }
    } finally {
  window.clearTimeout(timeoutTimer);

  if (!controller.signal.aborted) {
    setSimilarLoading(false);
  }
}
  }, 500);

  return () => {
    window.clearTimeout(debounceTimer);
    controller.abort();
  };
}, [
  subject,
  description,
  context,
  instance,
  preview,
  session,
  similarRetry,
]);
  const complete = !!context && !!subject.trim() && !!channel;
  const selectedProduct = context?.instances.find(
    (item) => item.id === instance,
  );
  async function submitSimilarityDecision() {
  if (!similarFeedbackId || !similarDecision || decisionSaving) return;

  if (similarDecision !== "new" && !chosenSimilarId) {
    setSimilarError("กรุณาเลือกเคสที่ต้องการอ้างอิงก่อน");
    return;
  }

  setDecisionSaving(true);
  setSimilarError("");

  try {
    await api(`/tickets/similarity-feedback/${similarFeedbackId}`, {
      method: "POST",
      body: JSON.stringify({
        decision: similarDecision,
        chosen_ticket_id:
          similarDecision === "new" ? null : chosenSimilarId,
      }),
    });

    if (similarDecision === "reuse") {
      const selected = similarItems.find(
        (item) => item.id === chosenSimilarId,
      );

      if (selected) {
        if (selected.product_instance_id) {
          setInstance(selected.product_instance_id);
        }

        if (selected.category_id) {
          setCategory(String(selected.category_id));
        }

        setMessage("เลือกใช้ข้อมูลจากเคสเดิมแล้ว กรุณาตรวจสอบข้อมูลก่อนสร้างเคส");
      }
   } else if (similarDecision === "link") {
  setMessage(
    "บันทึกการตัดสินใจแล้ว การสร้างความสัมพันธ์ระหว่างเคสจะดำเนินการเมื่อพัฒนา REL"
  );
} else {
      setMessage("บันทึกการเลือกเปิดการสอบสวนใหม่แล้ว");
    }
  } catch (e) {
    setSimilarError(
      e instanceof Error ? e.message : "บันทึกผลการเลือกไม่สำเร็จ",
    );
  } finally {
    setDecisionSaving(false);
  }
}

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
          created_for_user_id: createdFor ? Number(createdFor) : null,
        }),
      });
      for (const f of files) {
  const fd = new FormData();
  fd.append("file", f);
  await api(`/tickets/${ticket.id}/attachments`, { method: "POST", body: fd });
}
      router.push(href(`/cases/${ticket.id}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกเคสไม่สำเร็จ");
    } finally {
      setSaving(false);
    }
  }

const [createdFor, setCreatedFor] = useState("");
const [members, setMembers] = useState<{ id: number; name: string }[]>([]);
useEffect(() => {
  if (preview) return;
  api<{ id: number; name: string }[]>("/tickets/team-members").then(setMembers).catch(() => {});
}, [preview]);
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
              <label className="subject-field" htmlFor="case-subject">
                หัวข้อ <span className="required">*</span>
                <Input
                  id="case-subject"
                  aria-label="หัวข้อ *"
                  value={subject}
                  maxLength={255}
                  placeholder="ระบุเรื่องที่ต้องการแจ้งให้เข้าใจง่าย"
                  onChange={setSubject}
                />
              </label>
              {!preview && (
  <section className="related-cases">
    <div className="related-heading">
      <h3>เคสที่คล้ายกัน</h3>
      <button
        type="button"
        className="button button-secondary button-sm"
        onClick={() => setSimilarRetry((value) => value + 1)}
        disabled={similarLoading}
      >
        ค้นหาเคสคล้ายอีกครั้ง
      </button>
    </div>

    {similarLoading && <p>กำลังค้นหาเคสที่คล้ายกัน...</p>}

    {similarError && (
      <p className="form-error" role="alert">
        {similarError}
      </p>
    )}

    {!similarLoading && similarityQuery.length < 10 && (
      <p>กรอกหัวข้อหรือรายละเอียดอย่างน้อย 10 ตัวอักษรเพื่อค้นหา</p>
    )}

    {!similarLoading && similarityQuery.length >= 10 &&
      similarItems.length === 0 && (
        <p>ยังไม่พบเคสที่คล้ายกัน คุณสามารถสร้างเคสใหม่ได้</p>
      )}

    {similarItems.map((item) => (
      <div className="related-case" key={item.id}>
        <span className="match-score">{item.score}%</span>

        <div className="related-subject">
          <strong>{item.ticket_no} · {item.subject}</strong>
          <small>
            {item.status} · {item.hint}
          </small>
          <small>
            {item.product} · {item.customer}
          </small>
        </div>

        <label>
          <input
            type="radio"
            name="similar-ticket"
            checked={chosenSimilarId === item.id}
            onChange={() => setChosenSimilarId(item.id)}
          />
          เลือกเคสนี้
        </label>

        <Link
          href={href(`/cases/${item.id}`)}
          className="button button-secondary button-sm"
        >
          <Eye size={12} />
          ดูเคส
        </Link>
      </div>
    ))}

    {similarFeedbackId && similarItems.length > 0 && (
      <div className="similarity-decision">
        <p><strong>คุณต้องการดำเนินการอย่างไร?</strong></p>

        <label>
          <input
            type="radio"
            name="similar-decision"
            checked={similarDecision === "reuse"}
            onChange={() => setSimilarDecision("reuse")}
          />
          ใช้วิธีแก้ไขจากเคสเดิม (Reuse)
        </label>

        <label>
          <input
            type="radio"
            name="similar-decision"
            checked={similarDecision === "link"}
            onChange={() => setSimilarDecision("link")}
          />
          เชื่อมโยงกับเคสเดิม (Link Existing)
        </label>

        <label>
          <input
            type="radio"
            name="similar-decision"
            checked={similarDecision === "new"}
            onChange={() => {
              setSimilarDecision("new");
              setChosenSimilarId(null);
            }}
          />
          เปิดการสอบสวนใหม่ (New Investigation)
        </label>

        <Button
          type="button"
          disabled={!similarDecision || decisionSaving ||
            (similarDecision !== "new" && !chosenSimilarId)}
          onClick={submitSimilarityDecision}
        >
          {decisionSaving ? "กำลังบันทึก..." : "ยืนยันการเลือก"}
        </Button>
      </div>
    )}
  </section>
)}
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
              {select(
  "สร้างแทนเพื่อนร่วมทีม (ไม่บังคับ)",
  createdFor,
  setCreatedFor,
  members,
  members.length === 0,
)}
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
                
<input type="file" multiple accept="image/jpeg,image/png,image/webp,application/pdf"
  onChange={(e) => setFiles(Array.from(e.target.files || []))} />
{files.map((f) => <small key={f.name}>{f.name}</small>)}
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
