"use client";
import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import {
  ArrowRightLeft,
  GitBranch,
  Inbox,
  List,
  Search,
  ClipboardList,
  BookOpen,
  Users,
  ChartNoAxesColumn,
  UsersRound,
  Database,
  Clock3,
  Zap,
  History,
  ChevronsLeft,
  Megaphone,
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
const ROLE_NAMES: Record<string, string> = {
  Admin: "ผู้ดูแลระบบ",
  Agent: "เจ้าหน้าที่ Tier 2",
  Specialist: "ผู้เชี่ยวชาญ Tier 1",
  Developer: "ทีมพัฒนา Tier 0",
  "Team Lead": "หัวหน้าทีม",
  Executive: "ผู้บริหาร",
};
const PREVIEW_PRODUCTS = [
  { code: "examplus", name: "ExamPlus" },
  { code: "geta", name: "GetA" },
  { code: "logbook", name: "Logbook" },
];
let productCache: Promise<{ code: string; name: string }[]> | null = null;
function productIcon(code: string): LucideIcon {
  return code === "logbook" ? BookOpen : code === "geta" ? ShieldCheck : MonitorCog;
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
  const [products, setProducts] = useState(preview ? PREVIEW_PRODUCTS : []);
  useEffect(() => {
    if (preview || !session) return;
    productCache ??= api<{ code: string | null; name: string }[]>(
      "/products?is_active=true&limit=100",
    )
      .then((rows) => rows.filter((row): row is { code: string; name: string } => !!row.code))
      .catch(() => {
        productCache = null;
        return [];
      });
    let active = true;
    productCache.then((rows) => active && setProducts(rows));
    return () => {
      active = false;
    };
  }, [preview, session]);
  const isAdmin = session?.role === "Admin" && !preview;
  const groups: { title: string; items: NavItem[] }[] = [
    {
      title: "งาน",
      items: [
        { label: "งานของฉัน", path: "/my-work", icon: Inbox, badge: counts?.mine },
        { label: "เคสทั้งหมด", path: "/cases", icon: List },
        {
          label: "ยังไม่มีผู้รับ",
          path: "/unassigned",
          icon: ClipboardList,
          badge: counts?.unassigned,
        },
        ...(!preview && session ? [{ label: "ค้นหาเคส", path: "/cases/search", icon: Search }] : []),
        ...(session?.can_create_cases
          ? [{ label: "ส่งมอบงาน", path: "/routing", icon: ArrowRightLeft }]
          : []),
      ],
    },
    ...(products.length
      ? [
          {
            title: "ผลิตภัณฑ์",
            items: products.map((product) => ({
              label: product.name,
              path: `/products/${product.code}`,
              icon: productIcon(product.code),
            })),
          },
        ]
      : []),
    {
      title: "ลูกค้า",
      items: [
        { label: "ทะเบียนลูกค้า", path: "/customers", icon: Users },
        ...(!preview && session && ["Admin", "Team Lead"].includes(session.role)
          ? [{ label: "ประกาศสถานะระบบ", path: "/announcements", icon: Megaphone }]
          : []),
      ],
    },
    ...(!preview && session && ["Admin", "Team Lead", "Executive"].includes(session.role)
      ? [
          {
            title: "รายงาน",
            items: [
              { label: "เวลาที่ใช้สร้างเคส", path: "/reports/capture-time", icon: Clock3 },
              ...(session.role === "Admin"
                ? [{ label: "แท็กยอดนิยม", path: "/reports/popular-tags", icon: ChartNoAxesColumn }]
                : []),
            ],
          },
        ]
      : []),
    ...(isAdmin
      ? [
          {
            title: "ตั้งค่าระบบ",
            items: [
              { label: "ผู้ใช้และทีม", path: "/administration/users", icon: UsersRound },
              { label: "ข้อมูลหลักและหมวดหมู่", path: "/master-data", icon: Database },
              { label: "SLA และเวลาทำการ", path: "/administration/sla-policies", icon: Clock3 },
              { label: "การส่งต่อเคส (Tier)", path: "/routing/admin", icon: GitBranch },
              { label: "กฎอัตโนมัติ", path: "/administration/automation", icon: Zap },
              { label: "ประวัติการแก้ไขข้อมูล", path: "/administration/audit-log", icon: History },
            ],
          },
        ]
      : []),
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
                const destination = href(item.path || "/my-work");
                const active =
                  !!item.path &&
                  (pathname === destination ||
                    (item.path === "/administration/users" &&
                      [
                        "/administration/teams",
                        "/administration/roles",
                      ].includes(pathname)) ||
                    (item.path === "/administration/sla-policies" &&
                      pathname === "/administration/business-calendars") ||
                    (item.path === "/master-data" &&
                      pathname.startsWith("/master-data/")) ||
                    (item.path === "/my-work" &&
                      pathname.endsWith("/cases/new")) ||
                    (destination.endsWith("/cases") &&
                      !pathname.endsWith("/cases/new") &&
                      pathname.startsWith(`${destination}/`)));
                return item.disabled ? (
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

                  </Link>
                );
              })}
            </section>
          ))}
        </nav>
        <div className="sidebar-account">
          <span className="avatar avatar-outline">
            {session?.username.slice(0, 2).toUpperCase() || "IS"}
          </span>
          <div>
            <strong>{session?.username || "ISMS"}</strong>
            <small>{ROLE_NAMES[session?.role || ""] || session?.role || ""}</small>
          </div>
          <ChevronsUpDown size={16} />
        </div>
      </aside>
    </>
  );
}
