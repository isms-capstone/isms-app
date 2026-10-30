"use client";
import { useState } from "react";
import {
  PanelLeftClose,
  ChevronRight,
  Bell,
  Search,
  LogOut,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useSession } from "@/components/providers/session-provider";
import { Button } from "@/components/ui/primitives";
export function TopBar({
  title,
  onToggle,
}: {
  title: string;
  onToggle: () => void;
}) {
  const { session, href, signOut } = useSession();
  const router = useRouter();
  const [query, setQuery] = useState("");
  return (
    <header className="top-bar">
      <div className="breadcrumb">
        <Button
          variant="ghost"
          size="icon"
          aria-label="เปิดหรือปิดเมนู"
          onClick={onToggle}
        >
          <PanelLeftClose size={19} />
        </Button>
        <span>หน้าหลัก</span>
        <ChevronRight size={12} />
        <strong>{title}</strong>
      </div>
      <div className="topbar-right">
        <form
          className="global-search"
          onSubmit={(event) => {
            event.preventDefault();
            router.push(`${href("/cases")}?q=${encodeURIComponent(query)}`);
          }}
        >
          <Search size={15} />
          <input
            aria-label="ค้นหาเคสจากทุกหน้า"
            placeholder="ค้นหาเคส..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </form>
        <span className="notification-icon" title="ยังไม่มีระบบแจ้งเตือน">
          <Bell size={19} />
        </span>
        <span className="topbar-divider" />
        <div className="user-menu">
          <span className="avatar avatar-square">
            {session?.username.slice(0, 2).toUpperCase()}
          </span>
          <div>
            <strong>{session?.username}</strong>
            <small>
              {session?.role === "Agent" ? "Tier 2" : session?.role}
            </small>
          </div>
          <Button
            variant="ghost"
            size="icon"
            aria-label="ออกจากระบบ"
            onClick={signOut}
          >
            <LogOut size={15} />
          </Button>
        </div>
      </div>
    </header>
  );
}
