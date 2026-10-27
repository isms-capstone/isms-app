import type { NextRequest } from "next/server";
// Next may normalize nextUrl to localhost behind its server. Compare the browser
// Origin with the actual incoming Host and forwarded protocol instead.
export function isSameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get("origin");
  const host = request.headers.get("host");
  const protocol =
    request.headers.get("x-forwarded-proto")?.split(",")[0].trim() ||
    request.nextUrl.protocol.replace(":", "");
  if (!origin || !host || !["http", "https"].includes(protocol)) return false;
  try {
    return new URL(origin).origin === new URL(`${protocol}://${host}`).origin;
  } catch {
    return false;
  }
}
