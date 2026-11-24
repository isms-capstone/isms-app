"use client";
import {
  Button as GetButton,
  TextInput,
  SecureInput,
  Toggle as GetToggle,
  EmptyState as GetEmptyState,
  Skeleton,
  TableCell,
  TableHeaderCell as GetTableHeaderCell,
  Checkbox as GetCheckbox,
  Tag,
  type TextInputProps,
  type TableHeaderCellProps,
  type CheckboxProps,
} from "@DeverhoodHT/get-design";
import {
  forwardRef,
  useId,
  type ButtonHTMLAttributes,
  type ReactNode,
} from "react";
export function cx(...values: (string | false | null | undefined)[]) {
  return values.filter(Boolean).join(" ");
}
export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "ghost";
    size?: "sm" | "md" | "lg" | "icon";
  }
>(function Button(
  { className, variant = "secondary", size = "md", children, ...props },
  ref,
) {
  return (
    <GetButton
      ref={ref}
      type="button"
      {...props}
      variant={
        variant === "primary"
          ? "filled"
          : variant === "ghost"
            ? "plain"
            : "outline"
      }
      size={size === "icon" ? "sm" : size}
      className={cx(
        "company-native-button",
        "ui-button",
        size && `ui-button-${size}`,
        className,
      )}
    >
      {children}
    </GetButton>
  );
});
type InputProps = Omit<
  TextInputProps,
  | "type"
  | "variant"
  | "prefix"
  | "suffix"
  | "classNames"
  | "styles"
  | "onPrefixClick"
  | "onSuffixClick"
> & {
  type?: React.HTMLInputTypeAttribute;
};
export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, maxLength, placeholder = "", type = "text", ...props },
  ref,
) {
  if (type === "password") {
    return (
      <SecureInput
        {...props}
        ref={ref}
        placeholder={placeholder}
        className={cx("company-input", className)}
      />
    );
  }
  if (type !== "text") {
    return (
      <input
        {...props}
        ref={ref}
        type={type}
        maxLength={maxLength}
        placeholder={placeholder}
        onChange={(event) => props.onChange?.(event.target.value)}
        className={cx("native-typed-input", className)}
      />
    );
  }
  return (
    <TextInput
      {...props}
      ref={ref}
      placeholder={placeholder}
      maxLength={maxLength}
      clearable={false}
      className={cx("company-input", className)}
    />
  );
});
export { TableCell };
export function Checkbox({ className, ...props }: CheckboxProps) {
  return (
    <GetCheckbox className={cx("company-checkbox", className)} {...props} />
  );
}
export function ToggleField({
  label,
  ...props
}: CheckboxProps & { label: string }) {
  const id = useId();
  return (
    <div className="company-toggle-field">
      <GetToggle {...props} id={id} aria-label={label} size="md" />
      <label htmlFor={id}>{label}</label>
    </div>
  );
}
export function TableHeaderCell(props: TableHeaderCellProps) {
  return <GetTableHeaderCell showDividers={false} {...props} />;
}
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return (
    <Tag
      label={typeof children === "string" ? children : undefined}
      variant="outline"
      data-tone={tone}
    >
      {typeof children === "string" ? undefined : children}
    </Tag>
  );
}
export function EmptyState({
  title = "ไม่มีเคสที่ต้องดำเนินการ",
  description = "ยังไม่พบเคสที่ตรงกับเงื่อนไขที่เลือก",
  children,
}: {
  title?: string;
  description?: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <GetEmptyState
        title={<span role="heading" aria-level={3}>{title}</span>}
        description={description}
        variant="neutral"
      />
      {children}
    </div>
  );
}
export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <div role="alert" className="error-state">
      <strong>ไม่สามารถโหลดข้อมูลได้</strong>
      <p>{message}</p>
      <Button onClick={onRetry}>ลองอีกครั้ง</Button>
    </div>
  );
}
export function TableSkeleton() {
  return (
    <div aria-label="กำลังโหลดคิวเคส" role="status" className="table-skeleton">
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i}>
          <Skeleton height={12} />
          <Skeleton height={12} />
          <Skeleton height={12} />
          <Skeleton height={12} />
        </div>
      ))}
    </div>
  );
}
