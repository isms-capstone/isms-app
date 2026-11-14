import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  try {
    const form = await request.formData();
    const token = form.get("token");
    if (typeof token !== "string" || token.length > 3800) throw new Error();
    const backend = process.env.BACKEND_URL || "http://127.0.0.1:3000";
    const response = await fetch(`${backend}/api/v1/portal/sso-entry`, {
      method: "POST",
      body: new URLSearchParams({ token }),
      signal: AbortSignal.timeout(10000),
      redirect: "error",
    });
    if (!response.ok) throw new Error();
    const result = new NextResponse(null, {
      status: 303,
      headers: { Location: "/portal/report" },
    });
    result.cookies.set("isms_portal_grant", token, {
      httpOnly: true,
      sameSite: "lax",
      secure: request.nextUrl.protocol === "https:",
      path: "/api/portal",
      maxAge: 300,
    });
    result.headers.set("Cache-Control", "no-store");
    return result;
  } catch {
    const result = new NextResponse(null, {
      status: 303,
      headers: { Location: "/portal/report?entry=invalid" },
    });
    result.cookies.set("isms_portal_grant", "", {
      path: "/api/portal",
      maxAge: 0,
    });
    return result;
  }
}
