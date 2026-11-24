import { NextRequest, NextResponse } from "next/server";
import { isSameOrigin } from "@/lib/request-origin";
import { backendUrl } from "@/lib/portal-server";

export async function POST(request: NextRequest) {
  if (!isSameOrigin(request)) return NextResponse.json({ detail: "Invalid origin" }, { status: 403 });
  try {
    const { email } = await request.json();
    const upstream = await fetch(`${backendUrl()}/api/v1/portal/magic-link`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: String(email ?? "").slice(0, 320) }),
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    const data = await upstream.json();
    if (upstream.status === 422)
      return NextResponse.json({ detail: "กรุณากรอกอีเมลให้ถูกต้อง" }, { status: 422 });
    return NextResponse.json(data, { status: upstream.status });
  } catch {
    return NextResponse.json({ detail: "ส่งลิงก์ไม่สำเร็จ กรุณาลองใหม่" }, { status: 503 });
  }
}
