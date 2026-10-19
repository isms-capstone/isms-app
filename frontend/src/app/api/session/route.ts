import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { isSameOrigin } from "@/lib/request-origin";
const backend = () => process.env.BACKEND_URL || "http://127.0.0.1:3000";
export async function POST(request: NextRequest) {
  if (!isSameOrigin(request))
    return NextResponse.json({ detail: "Invalid origin" }, { status: 403 });
  try {
    const body = await request.json();
    if (typeof body.username !== "string" || typeof body.password !== "string")
      return NextResponse.json(
        { detail: "กรอกชื่อผู้ใช้และรหัสผ่าน" },
        { status: 400 },
      );
    const response = await fetch(`${backend()}/api/v1/auth/login`, {
      method: "POST",
      body: new URLSearchParams({
        username: body.username,
        password: body.password,
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    const data = await response.json();
    if (!response.ok)
      return NextResponse.json(
        {
          detail:
            typeof data.detail === "string"
              ? data.detail
              : "เข้าสู่ระบบไม่สำเร็จ",
        },
        { status: response.status },
      );
    const result = NextResponse.json({ ok: true });
    result.cookies.set("isms_access", data.access_token, {
      httpOnly: true,
      sameSite: "lax",
      secure: request.nextUrl.protocol === "https:",
      path: "/",
      maxAge: 3600,
    });
    return result;
  } catch {
    return NextResponse.json(
      { detail: "ไม่สามารถเชื่อมต่อ Backend ได้" },
      { status: 502 },
    );
  }
}
export async function DELETE(request: NextRequest) {
  if (!isSameOrigin(request))
    return NextResponse.json({ detail: "Invalid origin" }, { status: 403 });
  (await cookies()).delete("isms_access");
  return NextResponse.json({ ok: true });
}
