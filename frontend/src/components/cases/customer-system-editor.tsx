"use client";

import { useEffect, useState, type FormEvent } from "react";
import { SelectControl } from "@/components/ui/company-fields";
import { Button, Input } from "@/components/ui/primitives";
import { all, api } from "@/lib/api";
import type { Instance, Product } from "@/lib/types";

type CustomerSystem = Instance & { code: string; url: string };

export function CustomerSystemEditor({
  organizationId,
  onSaved,
  onCancel,
}: {
  organizationId: number;
  onSaved: (system: Instance) => void;
  onCancel: () => void;
}) {
  const [data, setData] = useState<{
    products: Product[];
    inactive: CustomerSystem[];
  } | null>(null);
  const [productId, setProductId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      all<Product>("/products?is_active=true", controller.signal),
      all<CustomerSystem>(
        `/product-instances?organization_id=${organizationId}&is_active=false`,
        controller.signal,
      ),
    ])
      .then(([products, inactive]) => {
        if (!controller.signal.aborted) setData({ products, inactive });
      })
      .catch(() => {
        if (!controller.signal.aborted)
          setError("โหลดข้อมูลระบบของลูกค้าไม่สำเร็จ");
      });
    return () => controller.abort();
  }, [organizationId, attempt]);

  async function save(action: () => Promise<Instance>) {
    setBusy(true);
    setError("");
    try {
      onSaved(await action());
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกระบบไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!productId || busy) return;
    const fields = Object.fromEntries(new FormData(event.currentTarget));
    void save(() =>
      api<Instance>(`/organizations/${organizationId}/products/${productId}/instances`, {
        method: "POST",
        body: JSON.stringify({ ...fields, is_active: true }),
      }),
    );
  }

  function activate(id: number) {
    void save(async () => {
      const path = `/product-instances/${id}`;
      const { code, name, version, environment, url } = await api<CustomerSystem>(path);
      return api<Instance>(path, {
        method: "PUT",
        body: JSON.stringify({ code, name, version, environment, url, is_active: true }),
      });
    });
  }

  return (
    <section className="case-system-editor" aria-label="จัดการระบบของลูกค้า">
      <h4>จัดการระบบของลูกค้า</h4>
      <p className="field-hint">เมื่อบันทึกแล้ว ระบบนี้จะถูกเลือกในฟอร์ม Resolve ให้ทันที</p>
      {!data && !error && <p role="status">กำลังโหลดข้อมูลระบบของลูกค้า…</p>}
      {error && <p role="alert" className="form-error">{error}</p>}
      {!data && error && (
        <Button onClick={() => { setError(""); setAttempt(attempt + 1); }}>ลองโหลดอีกครั้ง</Button>
      )}
      {!!data?.inactive.length && (
        <div className="case-system-fields">
          <strong>ระบบที่ปิดใช้งานอยู่</strong>
          <ul>
            {data.inactive.map((system) => (
              <li key={system.id}>
                <span>{system.name} · {system.environment}</span>
                <Button size="sm" disabled={busy} onClick={() => activate(system.id)}>
                  เปิดใช้งาน
                </Button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {data && (
        data.products.length ? (
          <form onSubmit={create} className="case-system-fields">
            <strong>เพิ่มระบบใหม่</strong>
            <fieldset className="detail-grid" disabled={busy}>
              <label>
                ผลิตภัณฑ์
                <SelectControl required value={productId} onValueChange={setProductId}>
                  <option value="">เลือกผลิตภัณฑ์</option>
                  {data.products.map((product) => (
                    <option key={product.id} value={product.id}>{product.name}</option>
                  ))}
                </SelectControl>
              </label>
              <label>ชื่อระบบ<Input name="name" required maxLength={255} placeholder="เช่น ระบบสอบของลูกค้า" /></label>
              <label>รหัสระบบ<Input name="code" required maxLength={50} placeholder="เช่น exam-production" /></label>
              <label>เวอร์ชัน<Input name="version" required maxLength={100} /></label>
              <label>Environment<Input name="environment" required maxLength={50} placeholder="เช่น production" /></label>
              <label>URL ของระบบ<Input name="url" type="url" required maxLength={2048} placeholder="https://" /></label>
            </fieldset>
            <div className="lifecycle-buttons">
              <Button type="submit" variant="primary" disabled={busy || !productId}>บันทึกระบบใหม่</Button>
            </div>
          </form>
        ) : <p className="field-hint">ยังไม่มีผลิตภัณฑ์ที่เปิดใช้งานสำหรับเพิ่มระบบใหม่</p>
      )}
      <Button variant="ghost" disabled={busy} onClick={onCancel}>กลับไปที่ฟอร์ม Resolve</Button>
    </section>
  );
}
