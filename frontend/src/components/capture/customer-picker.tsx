"use client";
import { useEffect, useRef, useState } from "react";
import { Search, ChevronUp, Building2, X } from "lucide-react";
import { api } from "@/lib/api";
import type { CustomerChoice, SelectionContext } from "@/lib/types";
import { Input, Button } from "@/components/ui/primitives";
export function CustomerPicker({
  value,
  onChange,
  onError,
}: {
  value: SelectionContext | null;
  onChange: (value: SelectionContext | null) => void;
  onError: (message: string) => void;
}) {
  const [query, setQuery] = useState(""),
    [choices, setChoices] = useState<CustomerChoice[]>([]),
    [open, setOpen] = useState(false),
    [loading, setLoading] = useState(false),
    [active, setActive] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null),
    selectionRef = useRef<AbortController | null>(null);
  useEffect(() => {
    if (!query.trim()) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setLoading(true);
      try {
        const data = await api<CustomerChoice[]>(
          `/customers/autocomplete?q=${encodeURIComponent(query)}`,
          { signal: controller.signal },
        );
        setChoices(data);
        setOpen(true);
        setActive(-1);
      } catch (e) {
        if (!controller.signal.aborted)
          onError(e instanceof Error ? e.message : "ค้นหาไม่สำเร็จ");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 180);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query, onError]);
  useEffect(() => () => selectionRef.current?.abort(), []);
  async function select(choice: CustomerChoice) {
    selectionRef.current?.abort();
    const controller = new AbortController();
    selectionRef.current = controller;
    setOpen(false);
    try {
      const context = await api<SelectionContext>(
        `/customers/organizations/${choice.organization.id}/selection-context${choice.contact ? `?contact_id=${choice.contact.id}` : ""}`,
        { signal: controller.signal },
      );
      if (!controller.signal.aborted) {
        onChange(context);
        setQuery("");
      }
    } catch (e) {
      if (!controller.signal.aborted)
        onError(e instanceof Error ? e.message : "โหลดข้อมูลลูกค้าไม่สำเร็จ");
    }
  }
  return (
    <div className="customer-picker">
      <label htmlFor="customer-search">
        ลูกค้า / ผู้แจ้ง <span className="required">*</span>
      </label>
      <div className="customer-picker-row">
        <div className="combobox-wrap">
          <div className="search-field">
            <Search size={16} />
            <Input
              ref={inputRef}
              id="customer-search"
              value={query}
              role="combobox"
              aria-expanded={open}
              aria-controls="customer-options"
              aria-autocomplete="list"
              aria-activedescendant={
                active >= 0 ? `customer-option-${active}` : undefined
              }
              placeholder="ค้นหาลูกค้าหรือผู้แจ้ง..."
              onBlur={() => setTimeout(() => setOpen(false), 150)}
              onChange={(value) => {
                selectionRef.current?.abort();
                setQuery(value);
                setOpen(!!value);
                if (!value) setChoices([]);
              }}
              onKeyDown={(event) => {
                if (event.key === "Escape") setOpen(false);
                if (event.key === "ArrowDown") {
                  event.preventDefault();
                  setActive((index) => Math.min(index + 1, choices.length - 1));
                }
                if (event.key === "ArrowUp") {
                  event.preventDefault();
                  setActive((index) => Math.max(index - 1, 0));
                }
                if (event.key === "Enter" && open && active >= 0) {
                  event.preventDefault();
                  select(choices[active]);
                }
              }}
            />
            <ChevronUp size={14} />
          </div>
          {open && (
            <div
              className="customer-options"
              role="listbox"
              id="customer-options"
            >
              {loading ? (
                <p>กำลังค้นหา...</p>
              ) : choices.length ? (
                choices.map((choice, index) => (
                  <button
                    type="button"
                    role="option"
                    aria-selected={active === index}
                    id={`customer-option-${index}`}
                    key={`${choice.organization.id}-${choice.contact?.id || 0}`}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => select(choice)}
                  >
                    <Building2 size={17} />
                    <span>
                      <strong>{choice.organization.name}</strong>
                      <small>{choice.contact?.name || "องค์กรลูกค้า"}</small>
                    </span>
                  </button>
                ))
              ) : (
                <p>ไม่พบลูกค้า · เพิ่มได้ที่ทะเบียนลูกค้า</p>
              )}
            </div>
          )}
        </div>
        {value && (
          <div className="selected-customer">
            <span className="customer-square">
              <Building2 size={20} />
            </span>
            <span>
              <strong>{value.organization.name}</strong>
              <small>{value.contact?.name || "องค์กรลูกค้า"}</small>
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                onChange(null);
                inputRef.current?.focus();
              }}
            >
              เปลี่ยน
              <X size={12} />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
