import { NextRequest, NextResponse } from "next/server";
import { isSameOrigin } from "@/lib/request-origin";
import { PORTAL_SESSION, backendUrl } from "@/lib/portal-server";

// Only these customer resources are reachable through the portal proxy.
const ALLOWED = [/^me$/, /^me\/cases$/, /^me\/cases\/[A-Z0-9-]{1,32}$/, /^announcements$/];

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const resource = path.join("/");
  if (!ALLOWED.some((rule) => rule.test(resource)))
    return NextResponse.json({ detail: "ไม่พบหน้าที่ต้องการ" }, { status: 404 });
  if (request.method !== "GET" && !isSameOrigin(request))
    return NextResponse.json({ detail: "Invalid origin" }, { status: 403 });
  const session = request.cookies.get(PORTAL_SESSION)?.value || "";
  if (!session && resource !== "announcements")
    return NextResponse.json({ detail: "กรุณาเข้าสู่ระบบ" }, { status: 401 });
  if (request.method === "POST" && Number(request.headers.get("content-length")) > 11 * 1024 * 1024)
    return NextResponse.json({ detail: "ภาพต้องมีขนาดไม่เกิน 10 MB" }, { status: 413 });
  try {
    const upstream = await fetch(`${backendUrl()}/api/v1/portal/${resource}${request.nextUrl.search}`, {
      method: request.method,
      headers: {
        "X-Portal-Session": session,
        "User-Agent": request.headers.get("user-agent") ?? "",
      },
      body: request.method === "POST" ? await request.formData() : undefined,
      cache: "no-store",
      signal: AbortSignal.timeout(15000),
      redirect: "error",
    });
    const text = await upstream.text();
    let data: unknown;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { detail: "ระบบขัดข้องชั่วคราว กรุณาลองใหม่" };
    }
    return NextResponse.json(data, { status: upstream.status, headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ detail: "เชื่อมต่อระบบไม่ได้ กรุณาลองใหม่" }, { status: 503 });
  }
}

export const GET = proxy;
export const POST = proxy;
