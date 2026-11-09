"use client";

import Link from "next/link";
import { useEffect, useId, useState, type FormEvent } from "react";
import { Database, Plus, Search } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import { SelectControl, TextArea } from "@/components/ui/company-fields";
import { Button, Input } from "@/components/ui/primitives";
import { all, api } from "@/lib/api";
import { masterCollections, type Collection } from "./master-data-config";

type Row = {
  id: number;
  name: string;
  is_active: boolean;
} & Record<string, string | number | boolean | null>;

export function MasterDataScreen({ section }: { section: string }) {
  const { session } = useSession();
  const permitted = Object.entries(masterCollections).filter(([, item]) =>
    item.registry ? session?.can_edit_customers : session?.role === "Admin",
  );
  const selected = permitted.find(([key]) => key === section);

  return (
    <AppShell title="Master Data">
      <div className="page-heading master-data-heading">
        <div>
          <h1>
            <Database aria-hidden="true" size={23} /> ข้อมูลหลัก
          </h1>
          <p>จัดการตัวเลือกในฟอร์มเคสและระบบที่ลูกค้าใช้งาน</p>
        </div>
      </div>
      {permitted.length > 0 && (
        <nav className="master-data-nav" aria-label="หมวดข้อมูลหลัก">
          {permitted.map(([key, item]) => (
            <Link
              key={key}
              href={`/master-data/${key}`}
              aria-current={key === section ? "page" : undefined}
            >
              {item.title}
            </Link>
          ))}
        </nav>
      )}
      {selected ? (
        <MasterDataCollection
          key={section}
          section={section}
          config={selected[1]}
        />
      ) : (
        <p className="surface master-data-card">
          ไม่พบหมวดข้อมูล หรือบัญชีนี้ไม่มีสิทธิ์จัดการหมวดดังกล่าว
        </p>
      )}
    </AppShell>
  );
}

export function MasterDataCollection({
  section,
  config,
}: {
  section: string;
  config: Collection;
}) {
  const [data, setData] = useState<{
    rows: Row[];
    references: Record<string, Row[]>;
  }>();
  const [editor, setEditor] = useState<Row | "new" | null>(null);
  const [values, setValues] = useState<Record<string, string>>({});
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [child, setChild] = useState<Row | null>(null);
  const titleId = useId();
  const systems = section === "customer-systems";
  const users = section === "users";
  const title = (row: Row) => String(row[config.titleKey ?? "name"]);

  useEffect(() => {
    const controller = new AbortController();
    const read = (path: string) => {
      if (path === "/admin/users")
        return all<Row>(path, controller.signal, "skip");
      if (
        [
          "/customers/organizations",
          "/product-instances",
          "/products",
        ].includes(path)
      )
        return all<Row>(path, controller.signal);
      return api<Row[]>(path, { signal: controller.signal });
    };
    const sources = [
      ...new Set(
        config.fields.flatMap((field) => [
          ...(field.source ? [field.source] : []),
          ...Object.values(field.sourceBy ?? {}).flatMap((option) =>
            option.source ? [option.source] : [],
          ),
        ]),
      ),
    ];
    Promise.all([
      read(config.path),
      Promise.all(
        sources.map(async (source) => [source, await read(source)] as const),
      ),
    ])
      .then(([rows, references]) => {
        if (!controller.signal.aborted)
          setData({ rows, references: Object.fromEntries(references) });
      })
      .catch((e: Error) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [config, attempt]);

  function start(row: Row | "new") {
    setEditor(row);
    setError("");
    setNotice("");
    setValues(
      Object.fromEntries(
        config.fields.map((field) => [
          field.key,
          String(
            (row === "new" ? undefined : row[field.key]) ??
              field.defaultValue ??
              "",
          ),
        ]),
      ),
    );
  }

  async function mutate(
    path: string,
    method: string,
    body: object | undefined,
    message: string,
    removedId?: number,
  ) {
    if (busy) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const saved = await api<Row | null>(path, {
        method,
        body: JSON.stringify(body),
      });
      setData(
        (current) =>
          current && {
            ...current,
            rows: !saved
              ? current.rows.filter((row) => row.id !== removedId)
              : current.rows.some((row) => row.id === saved.id)
                ? current.rows.map((row) => (row.id === saved.id ? saved : row))
                : [...current.rows, saved],
          },
      );
      setEditor(null);
      setNotice(message);
    } catch (e) {
      setError(e instanceof Error ? e.message : "บันทึกข้อมูลไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  const fields = config.fields
    .filter((field) => editor === "new" || !field.createOnly)
    .map((field) => ({
      ...field,
      optional: field.optional || (editor !== "new" && field.optionalOnEdit),
    }));

  function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!editor) return;
    const body = Object.fromEntries(
      fields
        .filter((field) => !field.optionalOnEdit || values[field.key])
        .map((field) => [
          field.key,
          field.type === "boolean"
            ? values[field.key] === "true"
            : field.source || field.type === "number"
              ? values[field.key]
                ? Number(values[field.key])
                : null
              : field.type === "password"
                ? values[field.key]
                : values[field.key].trim(),
        ]),
    );
    if (users) {
      const role = data?.references["/roles"]?.find(
        (role) => role.id === body.role_id,
      )?.name;
      if (!role) {
        setError("กรุณาเลือกบทบาทของผู้ใช้");
        return;
      }
      body.role = role;
      delete body.role_id;
    }
    if (editor === "new") {
      if (systems) {
        const { organization_id, product_id, ...instance } = body;
        void mutate(
          `/organizations/${organization_id}/products/${product_id}/instances`,
          "POST",
          instance,
          "เพิ่มระบบแล้ว",
        );
      } else {
        void mutate(config.path, "POST", body, "เพิ่มข้อมูลแล้ว");
      }
    } else {
      void mutate(
        `${config.path}/${editor.id}`,
        config.registry ? "PUT" : "PATCH",
        config.registry ? { ...body, is_active: editor.is_active } : body,
        "บันทึกการแก้ไขแล้ว",
      );
    }
  }

  function toggle(row: Row) {
    const is_active = !row.is_active;
    if (users) {
      void mutate(
        `${config.path}/${row.id}/${is_active ? "activate" : "suspend"}`,
        "POST",
        undefined,
        is_active ? "เปิดใช้งานแล้ว" : "ระงับบัญชีแล้ว",
      );
      return;
    }
    const body = config.registry
      ? Object.fromEntries(
          fields
            .filter((field) => !field.createOnly)
            .map((field) => [field.key, row[field.key]]),
        )
      : {};
    void mutate(
      `${config.path}/${row.id}`,
      config.registry ? "PUT" : "PATCH",
      { ...body, is_active },
      is_active ? "เปิดใช้งานแล้ว" : "ปิดใช้งานแล้ว",
    );
  }

  function change(key: string, value: string) {
    const next = { ...values, [key]: value };
    const reset = new Set([key]);
    for (const field of fields) {
      if (field.dependsOn && reset.has(field.dependsOn)) {
        next[field.key] = "";
        reset.add(field.key);
      }
    }
    setValues(next);
  }

  const referenceFields = config.fields.filter((field) => field.source);
  const referenceName = (key: string, source: string, row: Row) =>
    data?.references[source]?.find((item) => item.id === row[key])?.name;
  const needle = query.trim().toLowerCase();
  const rows = data?.rows.filter(
    (row) =>
      (!status || row.is_active === (status === "active")) &&
      [
        title(row),
        row.code,
        row.description,
        row.environment,
        ...referenceFields.map((field) =>
          referenceName(field.key, field.source!, row),
        ),
      ].some((value) =>
        String(value ?? "")
          .toLowerCase()
          .includes(needle),
      ),
  );

  return (
    <section className="surface master-data-card" aria-labelledby={titleId}>
      <div className="master-data-toolbar">
        <div>
          <h2 id={titleId}>{config.title}</h2>
          {data && <p className="field-hint">{data.rows.length} รายการ</p>}
        </div>
        <Button
          variant="primary"
          disabled={!data || busy || editor !== null}
          onClick={() => start("new")}
        >
          <Plus size={16} aria-hidden="true" /> เพิ่มรายการ
        </Button>
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {notice && (
        <p className="form-message" role="status">
          {notice}
        </p>
      )}
      {!data &&
        (error ? (
          <Button
            onClick={() => {
              setError("");
              setAttempt(attempt + 1);
            }}
          >
            ลองอีกครั้ง
          </Button>
        ) : (
          <p role="status">กำลังโหลดข้อมูล…</p>
        ))}
      {editor && (
        <form className="master-data-editor" onSubmit={save}>
          <h3>{editor === "new" ? "เพิ่มรายการ" : `แก้ไข ${title(editor)}`}</h3>
          <div className="detail-grid">
            {fields.map((field) => {
              const dynamic = field.sourceBy?.[values[field.dependsOn ?? ""]];
              const source = field.source ?? dynamic?.source;
              const choices = field.choices ?? dynamic?.choices;
              return (
                <label key={field.key}>
                  {field.label}
                  {field.optional ? " (ไม่บังคับ)" : ""}
                  {field.type === "boolean" ? (
                    <SelectControl
                      value={values[field.key]}
                      onValueChange={(value) => change(field.key, value)}
                      disabled={busy}
                    >
                      <option value="true">ใช่</option>
                      <option value="false">ไม่ใช่</option>
                    </SelectControl>
                  ) : source || choices || field.sourceBy ? (
                    <SelectControl
                      value={values[field.key]}
                      onValueChange={(value) => change(field.key, value)}
                      required={!field.optional}
                      disabled={
                        busy ||
                        Boolean(field.dependsOn && !values[field.dependsOn])
                      }
                    >
                      <option value="">เลือก{field.label}</option>
                      {source
                        ? data?.references[source]
                            ?.filter(
                              (row) =>
                                (!field.dependsOn ||
                                  field.sourceBy ||
                                  String(row[field.dependsOn]) ===
                                    values[field.dependsOn]) &&
                                (row.is_active !== false ||
                                  String(row.id) === values[field.key]),
                            )
                            .map((row) => (
                              <option key={row.id} value={row.id}>
                                {row.name}
                              </option>
                            ))
                        : choices?.map((choice) => (
                            <option key={choice}>{choice}</option>
                          ))}
                    </SelectControl>
                  ) : field.type === "textarea" ? (
                    <TextArea
                      value={values[field.key]}
                      onValueChange={(value) => change(field.key, value)}
                      required={!field.optional}
                      maxLength={field.max}
                      rows={3}
                      disabled={busy}
                    />
                  ) : (
                    <Input
                      value={values[field.key]}
                      onChange={(value) => change(field.key, value)}
                      required={!field.optional}
                      maxLength={field.max}
                      type={field.type}
                      disabled={busy}
                    />
                  )}
                </label>
              );
            })}
          </div>
          <div className="master-data-actions">
            <Button
              type="submit"
              variant="primary"
              disabled={
                busy ||
                fields.some(
                  (field) => !field.optional && !values[field.key]?.trim(),
                )
              }
            >
              บันทึก
            </Button>
            <Button
              disabled={busy}
              onClick={() => {
                setEditor(null);
                setError("");
              }}
            >
              ยกเลิก
            </Button>
          </div>
        </form>
      )}
      {data && (
        <>
          <div className="master-data-filters">
            <Search size={16} aria-hidden="true" />
            <Input
              aria-label="ค้นหาข้อมูลหลัก"
              placeholder="ค้นหาชื่อ รหัส หรือข้อมูลที่เกี่ยวข้อง"
              value={query}
              onChange={setQuery}
            />
            {!config.noStatus && (
              <SelectControl
                aria-label="กรองสถานะ"
                value={status}
                onValueChange={setStatus}
              >
                <option value="">ทุกสถานะ</option>
                <option value="active">ใช้งาน</option>
                <option value="inactive">ปิดใช้งาน</option>
              </SelectControl>
            )}
          </div>
          {rows?.length ? (
            <div className="case-table-scroll">
              <table className="master-data-table">
                <thead>
                  <tr>
                    <th>ชื่อ / รายละเอียด</th>
                    {!config.noStatus && <th>สถานะ</th>}
                    <th>จัดการ</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => {
                    const locked = config.lockedNames?.includes(row.name);
                    return (
                      <tr key={row.id}>
                        <td>
                          <strong>{title(row)}</strong>
                          <small>
                            {[
                              row.code,
                              row.email,
                              row.full_name,
                              row.condition_field &&
                                `${row.condition_field} = ${row.condition_value}`,
                              row.timezone,
                              row.holiday_date,
                              ...referenceFields.map((field) =>
                                referenceName(field.key, field.source!, row),
                              ),
                              row.environment,
                              row.description,
                            ]
                              .filter(Boolean)
                              .join(" · ")}
                          </small>
                        </td>
                        {!config.noStatus && (
                          <td>
                            <span
                              className={`master-data-status ${row.is_active ? "active" : ""}`}
                            >
                              {row.is_active ? "ใช้งาน" : "ปิดใช้งาน"}
                            </span>
                          </td>
                        )}
                        <td>
                          <div className="master-data-actions">
                            {locked ? (
                              <span className="field-hint">บทบาทระบบ</span>
                            ) : (
                              <Button
                                size="sm"
                                disabled={busy || editor !== null}
                                onClick={() => start(row)}
                              >
                                แก้ไข
                              </Button>
                            )}
                            {!config.noStatus && (
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={busy || editor !== null}
                                onClick={() => toggle(row)}
                              >
                                {row.is_active ? "ปิดใช้งาน" : "เปิดใช้งาน"}
                              </Button>
                            )}
                            {config.removable && !locked && (
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={busy || editor !== null}
                                onClick={() => {
                                  if (
                                    window.confirm(`ลบ ${title(row)} หรือไม่?`)
                                  )
                                    void mutate(
                                      `${config.path}/${row.id}`,
                                      "DELETE",
                                      undefined,
                                      "ลบรายการแล้ว",
                                      row.id,
                                    );
                                }}
                              >
                                ลบ
                              </Button>
                            )}
                            {config.child && (
                              <Button size="sm" onClick={() => setChild(row)}>
                                {config.child.title}
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="field-hint">ไม่พบรายการ</p>
          )}
        </>
      )}
      {child && config.child && (
        <details className="capture-accordion" open key={child.id}>
          <summary>
            จัดการ{config.child.title} · {title(child)}
          </summary>
          <MasterDataCollection
            section={config.child.suffix}
            config={{
              ...config.child,
              title: `${config.child.title} · ${title(child)}`,
              path: `${config.path}/${child.id}/${config.child.suffix}`,
            }}
          />
        </details>
      )}
    </section>
  );
}
