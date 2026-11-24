"use client";
import { Announcements } from "@/components/portal/announcements";
import { PortalShell } from "@/components/portal/portal-shell";

export default function PortalStatus() {
  return (
    <PortalShell public>
      <div className="page-heading">
        <div>
          <h1>สถานะระบบ</h1>
          <p>เหตุขัดข้องที่ทีมกำลังแก้ไขอยู่ หากปัญหาของคุณตรงกับประกาศ ไม่ต้องแจ้งซ้ำ</p>
        </div>
      </div>
      <Announcements />
    </PortalShell>
  );
}
