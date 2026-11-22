"use client";
import { SelectControl } from "@/components/ui/company-fields";
import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import { Button, Checkbox } from "@/components/ui/primitives";
import {
  channelNames,
  severityNames,
  statusNames,
  tierNames,
  type Product,
} from "@/lib/types";
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
      {disabled && <p className="field-hint">ยังไม่ได้ตั้งนโยบาย SLA</p>}
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
          "สถานะ",
          "statuses",
          Object.entries(statusNames).filter(([key]) => key !== "DRAFT"),
        )}
        {group(
          "ผลิตภัณฑ์",
          "products",
          products.map((p) => [p.code, p.name]),
        )}
        {group(
          "ความรุนแรง",
          "priorities",
          Object.entries(severityNames).map(([v, label]) => [v, `${v} ${label}`]),
        )}
        {group("Tier", "tiers", Object.entries(tierNames).reverse())}
        {group("ช่องทาง", "channels", Object.entries(channelNames))}
        {group(
          "SLA",
          "sla",
          [
            ["breached", "เกิน SLA แล้ว"],
            ["risk", "ใกล้ครบกำหนด (เหลือไม่ถึง 25%)"],
            ["safe", "ทันเวลา"],
          ],
          !slaAvailable,
        )}
        <fieldset>
          <legend>ผู้ดำเนินการ</legend>
          {[
            ["any", "ทุกคน"],
            ["mine", "ฉัน"],
            ["unassigned", "ยังไม่มีผู้รับ"],
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
          <legend>วันที่สร้างเคส</legend>
          <SelectControl
            aria-label="วันที่สร้าง"
            value={value.date}
            onValueChange={(nextValue) =>
              onChange({ ...value, date: nextValue })
            }
          >
            <option value="any">ทุกช่วงเวลา</option>
            <option value="today">วันนี้</option>
            <option value="7days">7 วันที่ผ่านมา</option>
            <option value="custom">กำหนดเอง</option>
          </SelectControl>
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
