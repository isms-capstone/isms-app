import { NextRequest, NextResponse } from "next/server";
import { backendUrl, setPortalSession } from "@/lib/portal-server";

/** The e-mail link opens /portal/login, whose button POSTs here. A plain GET
 * never consumes the one-time token, so mail scanners cannot burn it. */
export async function POST(request: NextRequest) {
  const fail = NextResponse.redirect(new URL("/portal/login?error=link", request.url), 303);
  try {
    const form = await request.formData();
    const token = String(form.get("token") ?? "");
    const upstream = await fetch(`${backendUrl()}/api/v1/portal/magic-link/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    if (!upstream.ok) return relative(fail);
    const { session, max_age } = await upstream.json();
    return setPortalSession(relative(NextResponse.redirect(new URL("/portal", request.url), 303)), request, session, max_age);
  } catch {
    return relative(fail);
  }
}

// Keep the browser's host (absolute redirects may switch 127.0.0.1/localhost and lose cookies).
function relative(response: NextResponse) {
  const location = response.headers.get("location");
  if (location) response.headers.set("location", new URL(location).pathname + new URL(location).search);
  return response;
}
