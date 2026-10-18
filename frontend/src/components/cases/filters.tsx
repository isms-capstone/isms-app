"use client";
import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { Button, Checkbox } from "@/components/ui/primitives";
import { channelNames, statusNames, type Product } from "@/lib/types";
export type Filters = {
  statuses: string[];
  products: string[];
  priorities: string[];
  tiers: string[];
  channels: string[];
  sla: string[];
  assignee: string;
  date: string;
  from: string;
  to: string;
};
export const emptyFilters: Filters = {
  statuses: [],
  products: [],
  priorities: [],
  tiers: [],
  channels: [],
  sla: [],
  assignee: "any",
  date: "any",
  from: "",
  to: "",
};
export function FilterDrawer({
  open,
  onClose,
  value,
  onChange,
  onApply,
  products,
  slaAvailable,
}: {
  open: boolean;
  onClose: () => void;
  value: Filters;
  onChange: (value: Filters) => void;
  onApply: () => void;
  products: Product[];
  slaAvailable: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = ref.current;
    if (open && !dialog?.open) dialog?.showModal();
    else if (!open && dialog?.open) dialog.close();
  }, [open]);
  const toggle = (
    key: "statuses" | "products" | "priorities" | "tiers" | "channels" | "sla",
    item: string,
  ) =>
    onChange({
      ...value,
      [key]: value[key].includes(item)
        ? value[key].filter((v) => v !== item)
        : [...value[key], item],
    });
  const group = (
    title: string,
    key: "statuses" | "products" | "priorities" | "tiers" | "channels" | "sla",
    options: [string, string][],
    disabled = false,
  ) => (
    <fieldset disabled={disabled}>
      <legend>{title}</legend>
      {options.map(([id, label]) => (
        <Checkbox
          key={id}
          className="check-label"
          label={label}
          disabled={disabled}
          checked={value[key].includes(id)}
          onChange={() => toggle(key, id)}
        />
      ))}
      {disabled && <p className="field-hint">รอข้อมูลจากระบบ SLA</p>}
    </fieldset>
  );
  return (
    <dialog
      ref={ref}
      className="filter-drawer"
      onCancel={onClose}
      onClick={(event) => {
        if (
          event.target === event.currentTarget &&
          event.clientX < event.currentTarget.getBoundingClientRect().left
        )
          onClose();
      }}
      aria-labelledby="filter-title"
    >
      <div className="drawer-header">
        <h2 id="filter-title">ตัวกรองเคส</h2>
        <Button
          variant="ghost"
          size="icon"
          aria-label="ปิดตัวกรอง"
          onClick={onClose}
        >
          <X size={17} />
        </Button>
      </div>
      <div className="drawer-body">
        {group(
          "สถานะ (Status)",
          "statuses",
          Object.entries(statusNames).filter(([key]) => key !== "DRAFT"),
        )}
        {group(
          "ผลิตภัณฑ์ (Product)",
          "products",
          products.map((p) => [p.name, p.name]),
        )}
        {group(
          "Priority",
          "priorities",
          ["S1", "S2", "S3", "S4"].map((v) => [v, v]),
        )}
        {group(
          "Tier",
          "tiers",
          ["0", "1", "2"].map((v) => [v, `Tier ${v}`]),
        )}
        {group("ช่องทาง (Channel)", "channels", Object.entries(channelNames))}
        {group(
          "SLA",
          "sla",
          [
            ["breached", "SLA breached"],
            ["risk", "At risk"],
            ["safe", "On track"],
          ],
          !slaAvailable,
        )}
        <fieldset>
          <legend>ผู้รับผิดชอบ (Assignee)</legend>
          {[
            ["any", "Anyone"],
            ["mine", "Me"],
            ["unassigned", "Unassigned"],
          ].map(([id, label]) => (
            <label key={id} className="check-label">
              <input
                type="radio"
                name="assignee"
                checked={value.assignee === id}
                onChange={() => onChange({ ...value, assignee: id })}
              />
              {label}
            </label>
          ))}
        </fieldset>
        <fieldset>
          <legend>วันที่สร้าง (Date)</legend>
          <select
            aria-label="วันที่สร้าง"
            value={value.date}
            onChange={(e) => onChange({ ...value, date: e.target.value })}
          >
            <option value="any">ทุกช่วงเวลา</option>
            <option value="today">วันนี้</option>
            <option value="7days">7 วันที่ผ่านมา</option>
            <option value="custom">กำหนดเอง</option>
          </select>
          {value.date === "custom" && (
            <>
              <label className="date-label">
                ตั้งแต่
                <input
                  type="date"
                  value={value.from}
                  onChange={(e) => onChange({ ...value, from: e.target.value })}
                />
              </label>
              <label className="date-label">
                ถึง
                <input
                  type="date"
                  min={value.from}
                  value={value.to}
                  onChange={(e) => onChange({ ...value, to: e.target.value })}
                />
              </label>
            </>
          )}
        </fieldset>
      </div>
      <div className="drawer-footer">
        <Button onClick={() => onChange({ ...emptyFilters })}>
          ล้างทั้งหมด
        </Button>
        <Button variant="primary" onClick={onApply}>
          ใช้ตัวกรอง
        </Button>
      </div>
    </dialog>
  );
}
