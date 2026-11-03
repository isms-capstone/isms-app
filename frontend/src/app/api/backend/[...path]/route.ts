import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import { isSameOrigin } from "@/lib/request-origin";
import { backendContract } from "@/lib/backend-contract";
import { readBackendJson } from "@/lib/backend-response";
import {
  encodeWorklog,
  normalizeWorklog,
  parseWorklogInput,
} from "@/lib/worklog-contract";
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
    const backend = process.env.BACKEND_URL || "http://127.0.0.1:3000";
    const upstream = (resource: string, init: RequestInit = {}) =>
      fetch(`${backend}/api/v1/${resource}`, {
        ...init,
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        cache: "no-store",
        signal: AbortSignal.timeout(15000),
        redirect: "error",
      });
    if (
      request.method === "GET" &&
      path.length === 1 &&
      path[0] === "capabilities"
    ) {
      return NextResponse.json(await backendContract(backend), {
        headers: { "Cache-Control": "no-store" },
      });
    }
    const worklogPath =
      path.length === 3 &&
      path[0] === "tickets" &&
      /^\d+$/.test(path[1]) &&
      path[2] === "worklogs";
    const timelinePath =
      path.length === 3 &&
      path[0] === "tickets" &&
      /^\d+$/.test(path[1]) &&
      path[2] === "timeline";
    if (
      (worklogPath && request.method === "POST") ||
      (timelinePath && request.method === "GET")
    ) {
      const contract = await backendContract(backend);
      if (worklogPath) {
        let input;
        try {
          input = parseWorklogInput(await request.json());
        } catch (error) {
          return NextResponse.json(
            {
              detail:
                error instanceof Error
                  ? error.message
                  : "ข้อมูลข้อความไม่ถูกต้อง",
            },
            { status: 422 },
          );
        }
        if (!contract.worklogFormat)
          return NextResponse.json(
            { detail: "Backend ยังไม่รองรับการบันทึกข้อความ" },
            { status: 501 },
          );
        const response = await upstream(`tickets/${path[1]}/worklogs`, {
          method: "POST",
          body: JSON.stringify(encodeWorklog(input, contract.worklogFormat)),
        });
        const decoded = await readBackendJson(response);
        if (!decoded.validJson || !response.ok)
          return NextResponse.json(decoded.data, {
            status: decoded.status,
            headers: { "Cache-Control": "no-store" },
          });
        return NextResponse.json(
          normalizeWorklog(
            decoded.data as Record<string, unknown>,
            contract.worklogFormat,
          ),
          { status: response.status, headers: { "Cache-Control": "no-store" } },
        );
      }
      if (!contract.timeline && contract.worklogFormat) {
        // The merged backend exposes worklogs but no unified timeline. Keep its authorization checks.
        const response = await upstream(`tickets/${path[1]}/worklogs`);
        const decoded = await readBackendJson(response);
        if (!decoded.validJson || !response.ok)
          return NextResponse.json(decoded.data, { status: decoded.status });
        const rows = decoded.data;
        if (!Array.isArray(rows))
          return NextResponse.json(
            { detail: "Backend ส่งข้อมูลไทม์ไลน์ไม่ถูกต้อง" },
            { status: 502 },
          );
        const events = rows.map((row: Record<string, unknown>) => {
          const item = normalizeWorklog(row, contract.worklogFormat);
          return { ...item, id: `worklog-${item.id}` };
        });
        events.sort(
          (
            a: { created_at: string; id: string },
            b: { created_at: string; id: string },
          ) =>
            a.created_at.localeCompare(b.created_at) ||
            Number(a.id.slice(8)) - Number(b.id.slice(8)),
        );
        const offset = Number(request.nextUrl.searchParams.get("offset") || 0);
        const limit = Number(request.nextUrl.searchParams.get("limit") || 100);
        if (
          !Number.isSafeInteger(offset) ||
          offset < 0 ||
          !Number.isSafeInteger(limit) ||
          limit < 1 ||
          limit > 500
        )
          return NextResponse.json(
            { detail: "Invalid pagination" },
            { status: 422 },
          );
        return NextResponse.json(
          {
            items: events.slice(offset, offset + limit),
            total: events.length,
            source: "worklogs",
          },
          { headers: { "Cache-Control": "no-store" } },
        );
      }
    }
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
