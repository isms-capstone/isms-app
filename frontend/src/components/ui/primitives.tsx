"use client";
import {
  Button as GetButton,
  InputText,
  Skeleton,
  TableCell,
  TableHeaderCell as GetTableHeaderCell,
  Checkbox as GetCheckbox,
  Tag,
  type InputTextProps,
  type TableHeaderCellProps,
  type CheckboxProps,
} from "@DeverhoodHT/get-design";
import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";
export function cx(...values: (string | false | null | undefined)[]) {
  return values.filter(Boolean).join(" ");
}
export const Button = forwardRef<
  HTMLButtonElement,
  ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: "primary" | "secondary" | "ghost";
    size?: "sm" | "icon";
  }
>(function Button(
  { className, variant = "secondary", size, children, ...props },
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
      size="sm"
      className={cx(
        "button",
        `button-${variant}`,
        size && `button-${size}`,
        className,
      )}
    >
      {children}
    </GetButton>
  );
});
export const Input = forwardRef<
  HTMLInputElement,
  Omit<InputTextProps, "variant">
>(function Input({ className, maxLength, placeholder = "", ...props }, ref) {
  return (
    <InputText
      ref={ref}
      {...props}
      placeholder={placeholder}
      variant={maxLength !== undefined ? "character-count" : "default"}
      maxLength={maxLength}
      className={cx("input company-input", className)}
    />
  );
});
export { TableCell };
export function Checkbox({ className, ...props }: CheckboxProps) {
  return (
    <GetCheckbox className={cx("company-checkbox", className)} {...props} />
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
      className={`badge badge-${tone}`}
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
      <h3>{title}</h3>
      <p>{description}</p>
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
