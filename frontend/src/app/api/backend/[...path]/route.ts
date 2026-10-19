import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { isSameOrigin } from "@/lib/request-origin";
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  if (!["GET", "HEAD"].includes(request.method) && !isSameOrigin(request))
    return NextResponse.json({ detail: "Invalid origin" }, { status: 403 });
  const token = (await cookies()).get("isms_access")?.value;
  if (!token)
    return NextResponse.json({ detail: "กรุณาเข้าสู่ระบบ" }, { status: 401 });
  const { path } = await context.params;
  if (
    path.some(
      (part) => part === ".." || part.includes("/") || part.includes("\\"),
    )
  )
    return NextResponse.json({ detail: "Invalid path" }, { status: 400 });
  try {
    const response = await fetch(
      `${process.env.BACKEND_URL || "http://127.0.0.1:3000"}/api/v1/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`,
      {
        method: request.method,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: ["GET", "HEAD"].includes(request.method)
          ? undefined
          : await request.text(),
        cache: "no-store",
        signal: AbortSignal.timeout(15000),
        redirect: "error",
      },
    );
    return new NextResponse(
      response.status === 204 ? null : await response.arrayBuffer(),
      {
        status: response.status,
        headers: {
          "Content-Type":
            response.headers.get("content-type") || "application/json",
          "Cache-Control": "no-store",
        },
      },
    );
  } catch {
    return NextResponse.json(
      { detail: "ไม่สามารถเชื่อมต่อ Backend ได้ กรุณาลองอีกครั้ง" },
      { status: 502 },
    );
  }
}
export { proxy as GET, proxy as POST, proxy as PATCH };
