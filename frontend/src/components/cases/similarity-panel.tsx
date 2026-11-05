"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, all } from "@/lib/api";
import type { Instance } from "@/lib/types";
import { useSession } from "@/components/providers/session-provider";
import { SelectControl, TextArea } from "@/components/ui/company-fields";
import { Button } from "@/components/ui/primitives";

export type ReuseValues = {
  product_instance_id: number;
  module_id: number | null;
  category_id: number | null;
  impact_scope:
    "organization" | "group" | "single_user" | "non_disruptive" | null;
  is_exam_window: boolean | null;
  severity_overridden_reason: string | null;
  severity: "S1" | "S2" | "S3" | "S4" | null;
  resolution_code_id: number | null;
  resolution_detail: string | null;
};
type SimilarCase = ReuseValues & {
  id: number;
  ticket_no: string | null;
  subject: string | null;
  product_id: number | null;
  source_type: string;
  status: string;
  hint: string;
  score: number;
  customer: string;
  product: string;
  assignee: string | null;
  last_activity: string;
};
type SearchResult = {
  feedback_id: number | null;
  items: SimilarCase[];
  decision_required: boolean;
  available: boolean;
};
type Props = {
  subject: string;
  description: string;
  organizationId: number | null;
  instanceId: number | null;
  ticketId?: number;
  autoSearch?: boolean;
  onState?: (feedbackId: number | null, blocked: boolean) => void;
  onReuse?: (values: ReuseValues) => void;
  onApplied?: () => void;
};

export function SimilarityPanel(props: Props) {
  const { href } = useSession();
  const {
    subject,
    description,
    organizationId,
    instanceId,
    ticketId,
    autoSearch = true,
  } = props;
  const callbacks = useRef(props);
  useEffect(() => {
    callbacks.current = props;
  });
  const [retry, setRetry] = useState(0);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [decision, setDecision] = useState<"reuse" | "link" | "new" | "">("");
  const [chosen, setChosen] = useState<number | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [reuse, setReuse] = useState<ReuseValues | null>(null);
  const [instances, setInstances] = useState<Instance[]>([]);
  const [options, setOptions] = useState<{
    modules: { id: number; name: string }[];
    problem_types: { id: number; name: string; module_id: number }[];
  } | null>(null);
  const [solutions, setSolutions] = useState<{ id: number; name: string }[]>(
    [],
  );
  const skipInstance = useRef<number | null>(null);
  const query = `${subject} ${description}`.trim();

  useEffect(() => {
    const controller = new AbortController();
    if (organizationId)
      all<Instance>(
        `/product-instances?organization_id=${organizationId}&is_active=true`,
        controller.signal,
      )
        .then(setInstances)
        .catch(() => {});
    return () => controller.abort();
  }, [organizationId]);

  useEffect(() => {
    const controller = new AbortController();
    const product = instances.find(
      (item) => item.id === reuse?.product_instance_id,
    );
    if (product)
      api<NonNullable<typeof options>>(
        `/products/${product.product_id}/case-options`,
        { signal: controller.signal },
      )
        .then(setOptions)
        .catch(() => {});
    return () => controller.abort();
  }, [instances, reuse?.product_instance_id]);

  useEffect(() => {
    const controller = new AbortController();
    api<{ solutions: { id: number; name: string }[] }>(
      "/categorization/options",
      {
        signal: controller.signal,
      },
    )
      .then((data) => setSolutions(data.solutions))
      .catch(() => {});
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (skipInstance.current === instanceId && skipInstance.current !== null) {
      skipInstance.current = null;
      return;
    }
    setResult(null);
    setConfirmed(false);
    setDecision("");
    setChosen(null);
    setReuse(null);
    setError("");
    setNotice("");
    setLoading(false);
    callbacks.current.onState?.(null, false);
    if ((!autoSearch && retry === 0) || query.length < 10) return;
    const controller = new AbortController();
    let timeout: ReturnType<typeof setTimeout> | undefined;
    // Prevent submitting stale results during debounce, with a fixed 1.5s request deadline.
    callbacks.current.onState?.(null, true);
    const debounce = setTimeout(async () => {
      setLoading(true);
      timeout = setTimeout(() => {
        controller.abort();
        setLoading(false);
        setResult(null);
        callbacks.current.onState?.(null, false);
      }, 1500);
      try {
        const params = new URLSearchParams({ q: query });
        if (organizationId)
          params.set("organization_id", String(organizationId));
        if (instanceId) params.set("product_instance_id", String(instanceId));
        if (ticketId) params.set("ticket_id", String(ticketId));
        const data = await api<SearchResult>(`/tickets/similar?${params}`, {
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setResult(data);
        callbacks.current.onState?.(null, Boolean(data.decision_required));
      } catch {
        if (!controller.signal.aborted)
          callbacks.current.onState?.(null, false);
        // SIM-10: search errors/timeouts are silent and must not block case capture.
      } finally {
        clearTimeout(timeout);
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 500);
    return () => {
      clearTimeout(debounce);
      clearTimeout(timeout);
      controller.abort();
    };
  }, [query, organizationId, instanceId, ticketId, retry, autoSearch]);

  function choose(id: number) {
    setChosen(id);
    setError("");
    const item = result?.items.find((row) => row.id === id);
    if (!item) return;
    const matches = instances.filter(
      (row) => row.product_id === item.product_id,
    );
    const instance =
      matches.find((row) => row.id === item.product_instance_id) ||
      matches.find((row) => row.id === instanceId) ||
      (matches.length === 1 ? matches[0] : null);
    setReuse({
      product_instance_id: instance?.id || 0,
      module_id: item.module_id,
      category_id: item.category_id,
      impact_scope: item.impact_scope,
      is_exam_window: item.is_exam_window,
      severity_overridden_reason: item.severity_overridden_reason,
      severity: item.severity,
      resolution_code_id: item.resolution_code_id,
      resolution_detail: item.resolution_detail,
    });
  }

  async function confirm() {
    if (
      !result?.feedback_id ||
      !decision ||
      saving ||
      (decision !== "new" && !chosen)
    )
      return;
    if (decision === "reuse" && !reuse?.product_instance_id) {
      setError("กรุณาเลือกผลิตภัณฑ์ของลูกค้าปัจจุบันก่อนใช้ข้อมูลเดิม");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const saved = await api<{ reuse_values: ReuseValues | null }>(
        `/tickets/similarity-feedback/${result.feedback_id}`,
        {
          method: "POST",
          body: JSON.stringify({
            decision,
            chosen_ticket_id: decision === "new" ? null : chosen,
            ticket_id: ticketId || null,
            reuse_values: decision === "reuse" ? reuse : null,
          }),
        },
      );
      if (decision === "reuse" && saved.reuse_values) {
        if (!ticketId && saved.reuse_values.product_instance_id !== instanceId)
          skipInstance.current = saved.reuse_values.product_instance_id;
        callbacks.current.onReuse?.(saved.reuse_values);
      }
      setConfirmed(true);
      callbacks.current.onState?.(result.feedback_id, false);
      setNotice(
        ticketId
          ? "บันทึกผลการเลือกกับเคสแล้ว"
          : "ยืนยันแล้ว ผลการเลือกจะผูกกับเคสเมื่อบันทึก",
      );
      if (ticketId) callbacks.current.onApplied?.();
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกผลการเลือกไม่สำเร็จ");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="related-cases similarity-panel" aria-label="เคสที่คล้ายกัน">
      <div className="related-heading">
        <h3>เคสที่คล้ายกัน</h3>
        <Button
          type="button"
          disabled={loading || saving}
          onClick={() => setRetry((n) => n + 1)}
        >
          ค้นหาเคสคล้ายอีกครั้ง
        </Button>
      </div>
      {loading && <p role="status">กำลังค้นหาเคสที่คล้ายกัน...</p>}
      {query.length < 10 && (
        <p>กรอกหัวข้อหรือรายละเอียดอย่างน้อย 10 ตัวอักษร</p>
      )}
      {result?.available && result.items.length === 0 && (
        <p>ยังไม่พบเคสที่คล้ายกัน</p>
      )}
      {result?.items.map((item) => (
        <div className="related-case" key={item.id}>
          <span className="match-score">{item.score}%</span>
          <div className="related-subject">
            <strong>
              {item.ticket_no} · {item.subject}
            </strong>
            <small>
              แหล่งที่มา: เคส · {item.status} · {item.hint}
            </small>
            <small>
              {item.product} · {item.customer} · ผู้รับผิดชอบ:{" "}
              {item.assignee || "ยังไม่ระบุ"}
            </small>
            <small>
              ล่าสุด: {new Date(item.last_activity).toLocaleString("th-TH")}
            </small>
          </div>
          <label>
            <input
              type="radio"
              name={`similar-ticket-${ticketId || "capture"}`}
              disabled={confirmed || saving}
              checked={chosen === item.id}
              onChange={() => choose(item.id)}
            />
            เลือกเคสนี้
          </label>
          <Link href={href(`/cases/${item.id}`)}>ดูเคส</Link>
        </div>
      ))}
      {result?.feedback_id && (
        <fieldset className="similarity-decision" disabled={confirmed || saving}>
          <legend>
            {result.decision_required
              ? "กรุณาเลือกแนวทางก่อนบันทึกเคส"
              : "เลือกแนวทาง (ถ้าต้องการ)"}
          </legend>
          {(
            [
              ["reuse", "ใช้วิธีแก้เดิม"],
              ["link", "ผูกกับรายการเดิม"],
              ["new", "เปิดสอบสวนใหม่"],
            ] as const
          ).map(([key, label]) => (
            <label key={key}>
              <input
                type="radio"
                name={`similar-decision-${ticketId || "capture"}`}
                checked={decision === key}
                onChange={() => setDecision(key)}
              />
              {label}
            </label>
          ))}
          {decision === "reuse" && reuse && (
            <div className="detail-grid">
              <label>
                ผลิตภัณฑ์ของลูกค้าปัจจุบัน
                <SelectControl
                  value={reuse.product_instance_id || ""}
                  onValueChange={(value) =>
                    setReuse({
                      ...reuse,
                      product_instance_id: Number(value),
                      module_id: null,
                      category_id: null,
                    })
                  }
                >
                  <option value="">เลือกผลิตภัณฑ์</option>
                  {instances.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} · {item.environment}
                    </option>
                  ))}
                </SelectControl>
              </label>
              <label>
                โมดูล
                <SelectControl
                  value={reuse.module_id || ""}
                  onValueChange={(value) =>
                    setReuse({
                      ...reuse,
                      module_id: Number(value) || null,
                      category_id: null,
                    })
                  }
                >
                  <option value="">ยังไม่ระบุ</option>
                  {options?.modules.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </SelectControl>
              </label>
              <label>
                หมวดหมู่
                <SelectControl
                  value={reuse.category_id || ""}
                  onValueChange={(value) =>
                    setReuse({
                      ...reuse,
                      category_id: Number(value) || null,
                    })
                  }
                >
                  <option value="">ยังไม่ระบุ</option>
                  {options?.problem_types
                    .filter(
                      (item) =>
                        !reuse.module_id || item.module_id === reuse.module_id,
                    )
                    .map((item) => (
                      <option key={item.id} value={item.id}>
                        {item.name}
                      </option>
                    ))}
                </SelectControl>
              </label>
              <label>
                ขอบเขตผลกระทบ
                <SelectControl
                  value={reuse.impact_scope || ""}
                  onValueChange={(value) =>
                    setReuse({
                      ...reuse,
                      impact_scope: (value ||
                        null) as ReuseValues["impact_scope"],
                    })
                  }
                >
                  <option value="">เลือกขอบเขตผลกระทบ</option>
                  <option value="organization">ทั้งองค์กร / ทั้งห้องสอบ</option>
                  <option value="group">บางกลุ่ม</option>
                  <option value="single_user">ผู้ใช้รายเดียว</option>
                  <option value="non_disruptive">ไม่กระทบการใช้งาน</option>
                </SelectControl>
              </label>
              <label>
                ระหว่างสอบจริง
                <SelectControl
                  value={
                    reuse.is_exam_window === null
                      ? ""
                      : String(reuse.is_exam_window)
                  }
                  onValueChange={(value) =>
                    setReuse({
                      ...reuse,
                      is_exam_window: value === "" ? null : value === "true",
                    })
                  }
                >
                  <option value="">ตรวจจากปฏิทิน</option>
                  <option value="true">ใช่</option>
                  <option value="false">ไม่ใช่</option>
                </SelectControl>
              </label>
              <label>
                เหตุผลปรับความรุนแรง
                <TextArea
                  value={reuse.severity_overridden_reason || ""}
                  maxLength={2000}
                  onValueChange={(value) =>
                    setReuse({
                      ...reuse,
                      severity_overridden_reason: value || null,
                    })
                  }
                />
              </label>
              <label>
                ความรุนแรง
                <SelectControl
                  value={reuse.severity || ""}
                  onValueChange={(value) =>
                    setReuse({
                      ...reuse,
                      severity: (value || null) as ReuseValues["severity"],
                    })
                  }
                >
                  <option value="">ยังไม่ระบุ</option>
                  {["S1", "S2", "S3", "S4"].map((value) => (
                    <option key={value}>{value}</option>
                  ))}
                </SelectControl>
              </label>
              <label>
                วิธีแก้
                <SelectControl
                  value={reuse.resolution_code_id || ""}
                  onValueChange={(value) =>
                    setReuse({
                      ...reuse,
                      resolution_code_id: Number(value) || null,
                    })
                  }
                >
                  <option value="">ยังไม่ระบุ</option>
                  {solutions.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </SelectControl>
              </label>
              <label>
                ขั้นตอนการแก้
                <TextArea
                  value={reuse.resolution_detail || ""}
                  maxLength={20000}
                  onValueChange={(value) =>
                    setReuse({
                      ...reuse,
                      resolution_detail: value || null,
                    })
                  }
                />
              </label>
            </div>
          )}
          <Button
            type="button"
            disabled={!decision || (decision !== "new" && !chosen)}
            onClick={confirm}
          >
            {saving ? "กำลังบันทึก..." : "ยืนยันการเลือก"}
          </Button>
        </fieldset>
      )}
      {notice && <p role="status">{notice}</p>}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
