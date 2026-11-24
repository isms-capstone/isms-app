import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const token = request.cookies.get("isms_portal_grant")?.value;
  if (!token) return NextResponse.json({ detail: "กรุณาเปิดจากผลิตภัณฑ์อีกครั้ง" }, { status: 401 });
  try {
    const backend = process.env.BACKEND_URL || "http://127.0.0.1:3000";
    const response = await fetch(`${backend}/api/v1/portal/status`, {
      method: "POST", body: new URLSearchParams({ token }),
      cache: "no-store", signal: AbortSignal.timeout(10000), redirect: "error",
    });
    return NextResponse.json(await response.json(), {
      status: response.status, headers: { "Cache-Control": "no-store" },
    });
  } catch {
    return NextResponse.json({ detail: "โหลดสถานะไม่สำเร็จ" }, { status: 503 });
  }
}
