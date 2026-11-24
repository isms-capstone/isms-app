import { NextRequest, NextResponse } from "next/server";
import { isSameOrigin } from "@/lib/request-origin";

export async function POST(request: NextRequest) {
  if (!isSameOrigin(request)) return NextResponse.json({ detail: "Invalid origin" }, { status: 403 });
  const token = request.cookies.get("isms_portal_grant")?.value;
  if (!token) return NextResponse.json({ detail: "กรุณาเปิดฟอร์มใหม่จากผลิตภัณฑ์" }, { status: 401 });
  const size = Number(request.headers.get("content-length"));
  if (size > 11 * 1024 * 1024) {
    return NextResponse.json({ detail: "ภาพต้องมีขนาดไม่เกิน 10 MB" }, { status: 413 });
  }
  try {
    const data = await request.formData();
    data.set("token", token);
    const backend = process.env.BACKEND_URL || "http://127.0.0.1:3000";
    const upstream = await fetch(`${backend}/api/v1/portal/cases`, {
      method: "POST", body: data, headers: { "User-Agent": request.headers.get("user-agent") ?? "" }, signal: AbortSignal.timeout(15000), redirect: "error",
    });
    const result = NextResponse.json(await upstream.json(), {
      status: upstream.status, headers: { "Cache-Control": "no-store" },
    });
    return result;
  } catch {
    return NextResponse.json({ detail: "ส่งเคสไม่สำเร็จ กรุณาลองอีกครั้ง" }, { status: 503 });
  }
}
