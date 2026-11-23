import type { NextRequest, NextResponse } from "next/server";

/** Server-only helpers for the customer portal. The session token lives in an
 * HttpOnly cookie scoped to /api/portal; browser code never reads it. */
export const PORTAL_SESSION = "isms_portal_session";
export const backendUrl = () => process.env.BACKEND_URL || "http://127.0.0.1:3000";

export function setPortalSession(
  response: NextResponse,
  request: NextRequest,
  session: string,
  maxAge: number,
) {
  response.cookies.set(PORTAL_SESSION, session, {
    httpOnly: true,
    sameSite: "lax",
    secure: request.nextUrl.protocol === "https:",
    path: "/api/portal",
    maxAge,
  });
  response.headers.set("Cache-Control", "no-store");
  return response;
}

export function clearPortalSession(response: NextResponse) {
  response.cookies.set(PORTAL_SESSION, "", { path: "/api/portal", maxAge: 0 });
  return response;
}
