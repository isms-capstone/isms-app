import { NextRequest, NextResponse } from "next/server";
import { isSameOrigin } from "@/lib/request-origin";
import { clearPortalSession } from "@/lib/portal-server";

export async function POST(request: NextRequest) {
  if (!isSameOrigin(request)) return NextResponse.json({ detail: "Invalid origin" }, { status: 403 });
  return clearPortalSession(NextResponse.json({ ok: true }));
}
