"use client";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Inbox,
  List,
  ClipboardList,
  BookOpen,
  Users,
  ChartNoAxesColumn,
  UsersRound,
  Database,
  Clock3,
  Zap,
  History,
  Settings,
  ChevronsLeft,
  ChevronRight,
  ChevronsUpDown,
  MonitorCog,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { useSession } from "@/components/providers/session-provider";
import { cx } from "@/components/ui/primitives";
type NavItem = {
  label: string;
  path?: string;
  icon: LucideIcon;
  badge?: number;
  disabled?: boolean;
};
export function CompanyMark() {
  return (
    <span className="company-mark">
      <Image
        src="/brand/deverhood.png"
        alt="Deverhood HT"
        width={62}
        height={52}
        priority
      />
    </span>
  );
}
export function Sidebar({
  open,
  onClose,
  counts,
}: {
  open: boolean;
  onClose: () => void;
  counts?: { mine: number; unassigned: number };
}) {
  const { session, href, preview } = useSession(),
    pathname = usePathname();
  const groups: { title: string; items: NavItem[] }[] = [
    {
      title: "WORK",
      items: [
        {
          label: "My Work",
          path: "/my-work",
          icon: Inbox,
          badge: counts?.mine,
        },
        { label: "All Cases", path: "/cases", icon: List },
        {
          label: "Unassigned",
          path: "/unassigned",
          icon: ClipboardList,
          badge: counts?.unassigned,
        },
      ],
    },
    {
      title: "PRODUCTS",
      items: [
        { label: "ExamPlus", path: "/products/examplus", icon: MonitorCog },
        { label: "GetA", path: "/products/geta", icon: ShieldCheck },
        { label: "Logbook", path: "/products/logbook", icon: BookOpen },
      ],
    },
    {
      title: "KNOWLEDGE",
      items: [{ label: "Knowledge Base", icon: BookOpen, disabled: true }],
    },
    {
      title: "CUSTOMERS",
      items: [{ label: "Customers", path: "/customers", icon: Users }],
    },
    {
      title: "REPORTS",
      items: [{ label: "Dashboard", icon: ChartNoAxesColumn, disabled: true }],
    },
    {
      title: "ADMINISTRATION",
      items: [
        { label: "Users & Teams", path: "/admin/", icon: UsersRound },
        { label: "Master Data", path: "/admin/", icon: Database },
        { label: "SLA & Business Hours", path: "/admin/", icon: Clock3 },
        { label: "Automation Rules", path: "/admin/", icon: Zap },
        { label: "Audit Log", icon: History, disabled: true },
      ],
    },
  ];
  return (
    <>
      {open && (
        <button
          className="sidebar-backdrop"
          onClick={onClose}
          aria-label="ปิดเมนู"
        />
      )}
      <aside className={cx("sidebar", open && "is-open")} aria-label="เมนูหลัก">
        <div className="brand">
          <Link
            href={href("/my-work")}
            onClick={onClose}
            className="brand-link"
          >
            <CompanyMark />
            <span>
              Deverhood HT<small>ISMS</small>
            </span>
          </Link>
          <button
            className="sidebar-collapse"
            aria-label="ย่อเมนู"
            onClick={onClose}
          >
            <ChevronsLeft size={18} />
          </button>
        </div>
        <nav>
          {groups.map((group) => (
            <section key={group.title} className="nav-group">
              <h2>{group.title}</h2>
              {group.items.map((item) => {
                const Icon = item.icon;
                const legacy = item.path === "/admin/";
                const destination = legacy
                  ? "/admin/"
                  : href(item.path || "/my-work");
                const active =
                  !!item.path &&
                  !legacy &&
                  (pathname === destination ||
                    (item.path === "/my-work" &&
                      pathname.endsWith("/cases/new")) ||
                    (destination.endsWith("/cases") &&
                      !pathname.endsWith("/cases/new") &&
                      pathname.startsWith(`${destination}/`)));
                return item.disabled ||
                  (legacy && (preview || !session?.can_edit_products)) ? (
                  <button
                    className="nav-item"
                    disabled
                    title="ยังไม่เปิดใช้งาน"
                    key={item.label}
                  >
                    <Icon />
                    <span>{item.label}</span>
                  </button>
                ) : (
                  <Link
                    key={item.label}
                    href={destination}
                    onClick={onClose}
                    className={cx("nav-item", active && "active")}
                    aria-current={active ? "page" : undefined}
                  >
                    <Icon />
                    <span>{item.label}</span>
                    {item.badge !== undefined && (
                      <span className="nav-count">{item.badge}</span>
                    )}
                    {group.title === "PRODUCTS" && (
                      <ChevronRight className="nav-chevron" />
                    )}
                  </Link>
                );
              })}
            </section>
          ))}
          <button
            className="nav-item settings-link"
            disabled
            title="ยังไม่เปิดใช้งาน"
          >
            <Settings />
            <span>Settings</span>
          </button>
        </nav>
        <div className="sidebar-account">
          <span className="avatar avatar-outline">
            {session?.username.slice(0, 2).toUpperCase() || "IS"}
          </span>
          <div>
            <strong>{session?.username || "ISMS"}</strong>
            <small>
              {session?.role === "Agent"
                ? "Tier 2"
                : session?.role || "Service Operations"}
            </small>
          </div>
          <ChevronsUpDown size={16} />
        </div>
      </aside>
    </>
  );
}
