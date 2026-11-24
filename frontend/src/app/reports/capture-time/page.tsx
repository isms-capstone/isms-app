"use client";
import { useEffect, useState } from "react";
import { Timer } from "lucide-react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import { SelectControl } from "@/components/ui/company-fields";
import { api } from "@/lib/api";

type Summary = {
  count: number;
  median_seconds: number | null;
  p90_seconds: number | null;
  within_target_pct: number | null;
};
type Report = {
  target_seconds: number;
  required_fields: string[];
  overall: Summary;
  users: (Summary & { user: string })[];
};
const VIEWERS = new Set(["Admin", "Team Lead", "Executive"]);
const seconds = (value: number | null) => (value === null ? "—" : `${Math.round(value)} วินาที`);

/** ADO-01/02 and CAP-04: capture time measured on real work. */
export default function CaptureTimeReport() {
  const { session } = useSession();
  const [days, setDays] = useState("30"),
    [report, setReport] = useState<Report | null>(null),
    [error, setError] = useState("");
  const allowed = !!session && VIEWERS.has(session.role);
  useEffect(() => {
    if (!allowed) return;
    const controller = new AbortController();
    api<Report>(`/reports/capture-time?days=${days}`, { signal: controller.signal })
      .then(setReport)
      .catch((e) => !controller.signal.aborted && setError(e.message));
    return () => controller.abort();
  }, [allowed, days]);

  return (
    <AppShell title="เวลาที่ใช้สร้างเคส">
      <div className="page-heading">
        <div>
          <h1>เวลาที่ใช้สร้างเคส</h1>
          <p>
            วัดจากการใช้งานจริง: เริ่มนับเมื่อผู้ใช้เริ่มกรอกหน้าสร้างเคส จนกดสร้างเคสสำเร็จ
            เป้าหมายโครงการคือไม่เกิน 30 วินาที (G-02, CAP-01)
          </p>
        </div>
        <label className="sort-control">
          ช่วงเวลา
          <SelectControl value={days} onValueChange={setDays} aria-label="ช่วงเวลา">
            <option value="7">7 วันล่าสุด</option>
            <option value="30">30 วันล่าสุด</option>
            <option value="90">90 วันล่าสุด</option>
          </SelectControl>
        </label>
      </div>
      {!allowed ? (
        <section className="surface detail-card">
          <p>รายงานนี้สำหรับผู้ดูแลระบบ หัวหน้าทีม และผู้บริหาร</p>
        </section>
      ) : (
        <>
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          {report && (
            <>
              <section className="surface detail-card">
                <h2 className="flex items-center gap-2">
                  <Timer size={17} aria-hidden /> ภาพรวม
                </h2>
                <dl className="portal-facts">
                  <div>
                    <dt>จำนวนเคสที่วัดได้</dt>
                    <dd>{report.overall.count.toLocaleString("th-TH")}</dd>
                  </div>
                  <div>
                    <dt>ค่ากลาง (median)</dt>
                    <dd>{seconds(report.overall.median_seconds)}</dd>
                  </div>
                  <div>
                    <dt>90% ใช้ไม่เกิน</dt>
                    <dd>{seconds(report.overall.p90_seconds)}</dd>
                  </div>
                  <div>
                    <dt>สร้างเสร็จภายใน {report.target_seconds} วินาที</dt>
                    <dd>{report.overall.within_target_pct === null ? "—" : `${report.overall.within_target_pct}%`}</dd>
                  </div>
                </dl>
                <p className="field-hint">
                  ช่องที่บังคับตอนสร้างเคสตอนนี้มี 3 ช่อง (ลูกค้า หัวข้อ ช่องทาง) การเพิ่มช่องบังคับต้องผ่านการอนุมัติ (ADO-04)
                </p>
              </section>
              <section className="surface detail-card">
                <h2>รายบุคคล</h2>
                {report.users.length === 0 ? (
                  <p className="text-muted">ยังไม่มีข้อมูลในช่วงนี้</p>
                ) : (
                  <table className="case-table">
                    <thead>
                      <tr>
                        <th>ผู้บันทึก</th>
                        <th>จำนวนเคส</th>
                        <th>ค่ากลาง</th>
                        <th>90% ไม่เกิน</th>
                        <th>ภายในเป้า</th>
                      </tr>
                    </thead>
                    <tbody>
                      {report.users.map((row) => (
                        <tr key={row.user}>
                          <td>{row.user}</td>
                          <td>{row.count}</td>
                          <td>{seconds(row.median_seconds)}</td>
                          <td>{seconds(row.p90_seconds)}</td>
                          <td>{row.within_target_pct}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                <p className="field-hint">
                  ใช้เพื่อปรับหน้าจอและหาค่าฐาน ไม่ใช่เพื่อประเมินรายบุคคลในช่วง 3 เดือนแรก (SRS 12.6)
                </p>
              </section>
            </>
          )}
        </>
      )}
    </AppShell>
  );
}
