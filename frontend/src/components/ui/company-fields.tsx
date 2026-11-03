"use client";
import {
  Select as GetSelect,
  TextInput,
  type TextInputProps,
} from "@DeverhoodHT/get-design";
import {
  Children,
  Fragment,
  isValidElement,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
  type OptionHTMLAttributes,
  type SelectHTMLAttributes,
} from "react";
import { cx } from "./primitives";

function optionList(
  children: ReactNode,
): { value: string; label: string; disabled?: boolean }[] {
  return Children.toArray(children).flatMap((child) => {
    if (!isValidElement<{ children?: ReactNode }>(child)) return [];
    if (child.type === Fragment) return optionList(child.props.children);
    const props = child.props as OptionHTMLAttributes<HTMLOptionElement>;
    if (child.type !== "option") return [];
    const label = Children.toArray(props.children).join("");
    return [
      { value: String(props.value ?? label), label, disabled: props.disabled },
    ];
  });
}

type SelectProps = Omit<
  SelectHTMLAttributes<HTMLSelectElement>,
  "onChange" | "value" | "defaultValue" | "size" | "multiple"
> & {
  value?: string | number;
  defaultValue?: string | number;
  onValueChange?: (value: string) => void;
};
/** Keep native form submission/validation while using the official custom menu.
 * The library forwards aria attributes to its hidden native select; explicitly
 * mirror its accessible name to the visible trigger for keyboard/screen readers. */
export function SelectControl({
  children,
  value,
  defaultValue,
  onValueChange,
  className,
  id,
  ...props
}: SelectProps) {
  const [selected, setSelected] = useState(String(defaultValue ?? ""));
  const [invalid, setInvalid] = useState(false);
  const root = useRef<HTMLSpanElement>(null);
  const generatedId = useId();
  const controlId = id ?? generatedId;
  const options = optionList(children);
  const current = value === undefined ? selected : String(value);
  useEffect(() => {
    const trigger = root.current?.querySelector<HTMLElement>(
      ".company-select-trigger",
    );
    if (!trigger) return;
    const label =
      props["aria-label"] ||
      Array.from(root.current?.closest("label")?.childNodes ?? [])
        .filter((node) => node.nodeType === Node.TEXT_NODE)
        .map((node) => node.textContent)
        .join(" ")
        .trim();
    trigger.id = controlId;
    if (label) trigger.setAttribute("aria-label", label);
    if (props["aria-labelledby"])
      trigger.setAttribute("aria-labelledby", props["aria-labelledby"]);
    if (props["aria-describedby"])
      trigger.setAttribute("aria-describedby", props["aria-describedby"]);
    if (props.required) trigger.setAttribute("aria-required", "true");
  }, [controlId, props]);
  return (
    <span
      className={cx("company-select", className)}
      ref={root}
      onClick={(event) => {
        // Stop the containing label from activating the hidden native select
        // after the visible menu trigger has already handled the click.
        if (!(event.target instanceof HTMLSelectElement))
          event.preventDefault();
      }}
    >
      <GetSelect
        {...props}
        id={`${controlId}-native`}
        value={current}
        options={options}
        size="md"
        placeholder={
          options.find((option) => option.value === "")?.label ?? "เลือกข้อมูล"
        }
        classNames={{ trigger: "company-select-trigger" }}
        error={invalid}
        notFoundContent="ไม่มีรายการให้เลือก"
        onInvalid={(event) => {
          event.preventDefault();
          setInvalid(true);
          root.current
            ?.querySelector<HTMLElement>(".company-select-trigger")
            ?.focus();
        }}
        onChange={(next) => {
          setSelected(next);
          setInvalid(false);
          onValueChange?.(next);
        }}
      />
      {invalid && (
        <small role="alert" className="field-error">
          กรุณาเลือกข้อมูล
        </small>
      )}
    </span>
  );
}

type TextAreaProps = Omit<
  TextInputProps,
  "type" | "onChange" | "value" | "defaultValue"
> & {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
};
export function TextArea({
  onValueChange,
  className,
  ...props
}: TextAreaProps) {
  return (
    <TextInput
      {...props}
      type="textarea"
      onChange={onValueChange}
      className={cx("company-textarea", className)}
    />
  );
}
