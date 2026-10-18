import {
  forwardRef,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
} from "react";
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
    <button
      ref={ref}
      type="button"
      {...props}
      className={cx(
        "button",
        `button-${variant}`,
        size && `button-${size}`,
        className,
      )}
    >
      {children}
    </button>
  );
});
export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement>
>(function Input({ className, ...props }, ref) {
  return <input ref={ref} {...props} className={cx("input", className)} />;
});
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
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
          <span />
          <span />
          <span />
          <span />
        </div>
      ))}
    </div>
  );
}
